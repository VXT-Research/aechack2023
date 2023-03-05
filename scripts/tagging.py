import os
import re
import signal
import ujson
import requests
import logging
import threading
from queue import Queue
import psycopg

DB_NAME = os.environ.get('POSTGRES_DB', 'aechack')
DB_CONNECTION = f"dbname={DB_NAME}"
MODEL_NAME = 'aechack-topics'
QUEUE_SIZE = 10
TAGGER_VERSION = 1

CREATE_TABLE_STATEMENT = """CREATE TABLE IF NOT EXISTS tags (
  model VARCHAR,
  data_type VARCHAR,
  original_id VARCHAR,
  tags JSON
);"""

SPAN_REGEX = re.compile(r'<[^>]+>')

exit_flag = threading.Event()

def run_tagging(settings=None):
    tokenized_document_queue = Queue(QUEUE_SIZE)
    tagged_document_queue = Queue(QUEUE_SIZE)

    reader_thread = threading.Thread(target=read_from_db, args=(tokenized_document_queue, ))
    tagger_thread = threading.Thread(target=tag, args=(tokenized_document_queue, tagged_document_queue))
    writer_thread = threading.Thread(target=write_to_db, args=(tagged_document_queue, ))

    # Start the threads
    reader_thread.start()
    tagger_thread.start()
    writer_thread.start()

    # Wait for threads to finish
    writer_thread.join()


def read_from_db(tokenized_document_queue):
    counter = 0
    with psycopg.connect(DB_CONNECTION) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT data_type, original_id, tokens FROM text_document")
            for data_type, original_id, tokens in cur:
                if exit_flag.is_set():
                    tokenized_document_queue.put(None)
                    break

                tokenized_document_queue.put((data_type, original_id, ujson.loads(tokens)))

                counter += 1
                if counter % 100 == 0:
                    logging.info(f"{counter}")

    print(f"Read {counter} documents")
    tokenized_document_queue.put(None)


def tag(tokenized_document_queue, tagged_document_queue):
    """ Reads documents from tokenized_document_queue and classifies them by calling vxt_explicit_tagger via RabbitMQ.
    Puts match objects returned by the tagger into tagged_document_queue.
    """

    while True:
        tup = tokenized_document_queue.get()

        # None markes then end of stream
        if tup is None:
            break

        data_type, original_id, tokens = tup

        model = 'aechack-topics'
        tags = _tag(model, tokens)
        if tags:
            tagged_document_queue.put((model, data_type, original_id, tags))

        model = 'aechack-ontology'
        tags = _tag(model, tokens)
        if tags:
            tagged_document_queue.put((model, data_type, original_id, tags))


    tagged_document_queue.put(None)


def _tag(model_name, tokens):
        response = requests.post(f'http://localhost:8010/{model_name}', json=tokens)
        json = response.json()

        # example: response = {
            # matches: [
            #     {
            #        'tag': 'Energiatehokkuus',
            #        'rule': 'aurinkokenno',
            #        'highlighted_text': '...',
            #        'paragraph_index': 6,
            #        'sentence_index': 4,
            #     },
            #     ...
            # ]
        # }

        tags = []
        for match in json:
            #match_text = re.sub(SPAN_REGEX, '', match['highlighted_text']).replace('\n', ' ')
            match_text = match['highlighted_text']

            tags.append({
                'tag': match['tag'],
                'rule': match['rule'],
                'text': match_text,
            })

            #if debug_counter % 100 == 0:
            #debug_counter += 1
            print(match['rule'])
            print(match_text)
            print('------------------------------------------')

        return tags


def write_to_db(tagged_document_queue):
    with psycopg.connect(DB_CONNECTION) as conn:
        with conn.cursor() as cur:
            cur.execute(CREATE_TABLE_STATEMENT);
            cur.execute("DELETE FROM tags");
            conn.commit();

            while True:
                tup = tagged_document_queue.get()

                # None marks then end of stream
                if tup is None:
                    break

                model, data_type, original_id, tags = tup

                cur.execute(
                    "INSERT INTO tags(model, data_type, original_id, tags) VALUES (%s, %s, %s, %s)",
                    (model, data_type, original_id, ujson.dumps(tags, ensure_ascii=False, escape_forward_slashes=False))
                )


def quit(signal, frame):
    logging.info("Quitting by request...")
    exit_flag.set()


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s : %(levelname)s : %(message)s')
    logging.getLogger('urllib3.connectionpool').setLevel(logging.ERROR)

    signal.signal(signal.SIGINT, quit)
    signal.signal(signal.SIGTERM, quit)

    run_tagging()
