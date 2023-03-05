import os
import psycopg
import numpy
import sklearn
from sklearn.preprocessing import StandardScaler
import umap
import ujson

DB_NAME = os.environ.get('POSTGRES_DB', 'aechack')
DB_CONNECTION = f"dbname={DB_NAME}"
DIM = 500
LIMIT = 1000

TOPIC_COLORS = {
    'default': '#808080',
    'Transportation': '#f00',
    'Energy': '#0f0',
    'Telecom': '#00f',
    'Water': '#ff0',
    'Demolition': '#0ff',
    'Renovation': '#f0f',
}

def load_tags(cur, model, data_type):
    result = {} # { original_id: tags }
    cur.execute(f"SELECT original_id, tags FROM tags WHERE model='{model}' AND data_type='{data_type}'")
    for original_id, tags in cur:
        result[original_id] = tags

    print(f"Loaded {len(result)} tags ({data_type}, {model})")

    return result


def load_tender_vectors(cur, only_ids):
    data_type = 'aechack_tender'
    total_counter = 0
    invalid_dim_counter = 0
    vector_counter = 0
    vectors = []
    ids = []
    metadata = {} # original_id => {'name': name}
    original_ids = {} # original_id

    # Load id -> original_id mapping
    cur.execute(f"SELECT id,original_id,meta_name,meta_cpv,meta_value,meta_description,meta_companies,meta_organization FROM {data_type}")

    for id, original_id, name, cpv, value, description, companies, organization in cur:
        if original_id not in only_ids:
            continue

        original_ids[id] = original_id
        metadata[original_id] = {
            'name': name,
            'cpv': cpv,
            'value': value,
            'description': description,
            'companies': companies,
            'organization': organization,
        }

    # Load vectors
    cur.execute(f"SELECT id,classname,document_vector FROM vector WHERE classname='{data_type}' AND category='content'")
    for id, data_type, vector in cur:
        original_id = original_ids.get(id)
        if not original_id:
            continue

        # Skip invalid vectors
        total_counter += 1
        if len(vector) != DIM:
            invalid_dim_counter += 1
            continue

        ids.append(original_id)
        vectors.append(vector)
        vector_counter += 1
        #if vector_counter >= LIMIT:
        #    break

    invalid_percentage = invalid_dim_counter * 100 / total_counter
    print(f"Loaded {len(vectors)} vectors, skipped {invalid_dim_counter} ({invalid_percentage:.0f}%) with invalid dim")

    return ids, vectors, metadata


def load_ontology_vectors(cur):
    data_type = 'aechack_ontology'
    vectors = []
    ids = []
    original_ids = {}

    # Load id -> original_id mapping
    for id,original_id in cur.execute(f"SELECT id,original_id FROM {data_type}"):
        original_ids[id] = original_id

    # Load vectors
    cur.execute(f"SELECT id,document_vector FROM vector WHERE classname='aechack_ontology' AND category='content'")
    for id, vector in cur:
        original_id = original_ids.get(id)
        if not original_id:
            continue

        vectors.append(vector)
        ids.append(original_id)

    return ids, vectors


def compute_umap(vectors):
    #reducer = sklearn.manifold.TSNE(n_components=3)
    reducer = umap.UMAP(metric='cosine', n_components=3)
    vectors = numpy.array(vectors)
    embeddings = reducer.fit_transform(vectors)
    scaled_embeddings = StandardScaler().fit_transform(embeddings)
    return scaled_embeddings


def render_tender(data_type, id, embedding, metadata, topic_tags, target_tags):
    document_topic_tags = topic_tags.get(id, [])
    document_target_tags = target_tags.get(id, [])
    meta = metadata[id]

    topic_color = TOPIC_COLORS['default']
    for tag in document_topic_tags:
       topic_color = TOPIC_COLORS[tag['tag']]
       break

    return {
        'type': data_type,
        'name': meta['name'],
        'cpv': meta['cpv'],
        'value': meta['value'],
        'description': meta['description'],
        'companies': meta['companies'],
        'organization': meta['organization'],
        'x': float(embedding[0]),
        'y': float(embedding[1]),
        'z': float(embedding[2]),
        'size': 0.03,
        'color': topic_color,
        'topic_tags': document_topic_tags,
        'target_tags': document_target_tags,
    }

def render_ontology(id, embedding, ontology_translations):
    translation = ontology_translations.get(id)

    if not translation:
        return None

    return {
        'name': translation,
        'x': float(embedding[0]),
        'y': float(embedding[1]),
        'z': float(embedding[2]),
    }


if __name__ == '__main__':
    ids = []
    data_types = []
    vectors = []
    metadata = {}
    with psycopg.connect(DB_CONNECTION) as conn:
        with conn.cursor() as cur:
            topic_tags = load_tags(cur, 'aechack-topics', 'aechack_tender')
            target_tags = load_tags(cur, 'aechack-ontology', 'aechack_tender')

            # Load tenders
            _ids, _vectors, metadata = load_tender_vectors(cur, topic_tags.keys())
            tender_count = len(_ids)
            ids.extend(_ids)
            vectors.extend(_vectors)
            data_types.extend(['aechack_tender' for i in range(0,len(_ids))])

            # Load ontology
            _ids, _vectors = load_ontology_vectors(cur)
            ids.extend(_ids)
            vectors.extend(_vectors)

    embeddings = compute_umap(vectors)

    with open('original_data/ontology-en.json') as f:
        ontology_translations = ujson.loads(f.read())

    # Render tenders
    result = []
    for data_type, id, embedding in zip(data_types[:tender_count], ids[:tender_count], embeddings[:tender_count]):
        result.append(render_tender(data_type, id, embedding, metadata, topic_tags, target_tags))

    with open('coordinates.json', 'w') as f:
        f.write(ujson.dumps(result, indent=2, ensure_ascii=False, escape_forward_slashes=False))
        f.write("\n")

    # Render ontology words
    result = []
    for id, embedding in zip(ids[tender_count:], embeddings[tender_count:]):
        json = render_ontology(id, embedding, ontology_translations)
        if json:
            result.append(json)

    with open('ontology.json', 'w') as f:
        f.write(ujson.dumps(result, indent=2, ensure_ascii=False, escape_forward_slashes=False))
        f.write("\n")
