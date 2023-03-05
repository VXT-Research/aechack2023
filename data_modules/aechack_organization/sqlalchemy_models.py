from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.dialects.postgresql import ARRAY, JSON
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class AechackOrganization(Base):
    __tablename__ = 'aechack_organization'

    id = Column(Integer, primary_key=True)
    original_id = Column(String, unique=True)
    created_at = Column(DateTime)
    updated_at = Column(DateTime)
    data_set = Column(String)

    # summary
    keywords = Column(ARRAY(String))
    preview = Column(String)

    # metadata
    meta_name = Column(String)
