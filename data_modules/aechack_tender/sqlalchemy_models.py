from sqlalchemy import Column, Integer, Float, String, DateTime
from sqlalchemy.dialects.postgresql import ARRAY, JSON
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class AechackTender(Base):
    __tablename__ = 'aechack_tender'

    id = Column(Integer, primary_key=True)
    original_id = Column(String, unique=True)
    created_at = Column(DateTime)
    updated_at = Column(DateTime)
    data_set = Column(String)

    # summary
    keywords = Column(ARRAY(String))
    preview = Column(String)

    # metadata
    meta_cloudia_id = Column(String)
    meta_name = Column(String)
    meta_description = Column(String)
    meta_cpv = Column(String)
    meta_value = Column(Float)
    meta_companies = Column(JSON)
    meta_organization = Column(JSON)
