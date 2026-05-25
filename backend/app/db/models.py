from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
from app.db.session import Base

class ScrapeJob(Base):
    __tablename__ = "scrape_jobs"

    id = Column(Integer, primary_key=True, index=True)
    query = Column(String, nullable=False, index=True)
    countries = Column(JSON, nullable=True)  # list of countries
    industries = Column(JSON, nullable=True)  # list of industries
    custom_keywords = Column(JSON, nullable=True)  # generated keywords for search
    fields_to_extract = Column(JSON, nullable=True)  # list of fields to extract
    max_pages = Column(Integer, default=5)
    concurrency = Column(Integer, default=5)
    export_format = Column(String, default="csv")
    
    # status: pending, running, completed, failed, cancelled
    status = Column(String, default="pending", index=True)
    total_discovered = Column(Integer, default=0)
    total_crawled = Column(Integer, default=0)
    total_leads = Column(Integer, default=0)
    progress = Column(Float, default=0.0)
    error_message = Column(Text, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    entities = relationship("Entity", back_populates="scrape_job", cascade="all, delete-orphan")
    failed_urls = relationship("FailedUrl", back_populates="scrape_job", cascade="all, delete-orphan")
    search_history = relationship("SearchHistory", back_populates="scrape_job", cascade="all, delete-orphan")
    extraction_schemas = relationship("ExtractionSchema", back_populates="scrape_job", cascade="all, delete-orphan")


class ExtractionSchema(Base):
    __tablename__ = "extraction_schemas"

    id = Column(Integer, primary_key=True, index=True)
    scrape_job_id = Column(Integer, ForeignKey("scrape_jobs.id"), nullable=False)
    field_name = Column(String, nullable=False)
    field_type = Column(String, default="text")  # text, email, phone, list
    created_at = Column(DateTime, default=datetime.utcnow)

    scrape_job = relationship("ScrapeJob", back_populates="extraction_schemas")


class Entity(Base):
    __tablename__ = "entities"

    id = Column(Integer, primary_key=True, index=True)
    scrape_job_id = Column(Integer, ForeignKey("scrape_jobs.id"), nullable=False)
    
    company_name = Column(String, nullable=True, index=True)
    website = Column(String, nullable=True)
    domain = Column(String, nullable=False, index=True)
    description = Column(Text, nullable=True)
    
    country = Column(String, nullable=True)
    address = Column(Text, nullable=True)
    
    classification = Column(String, default="unknown")  # manufacturer, distributor, hospital, tech company, startup, restaurant, logistics company, etc.
    industry = Column(String, nullable=True)  # inferred industry
    source = Column(String, nullable=True)
    contact_page = Column(String, nullable=True)
    
    status = Column(String, default="pending")  # pending, processing, crawled, failed
    extracted_data = Column(JSON, default=dict)  # JSON storing dynamic custom fields
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    scrape_job = relationship("ScrapeJob", back_populates="entities")
    contacts = relationship("Contact", back_populates="entity", cascade="all, delete-orphan")
    classifications = relationship("Classification", back_populates="entity", cascade="all, delete-orphan")


class Contact(Base):
    __tablename__ = "contacts"

    id = Column(Integer, primary_key=True, index=True)
    entity_id = Column(Integer, ForeignKey("entities.id"), nullable=False)
    
    type = Column(String, nullable=False)  # email, phone, whatsapp, linkedin, facebook, instagram, twitter, etc.
    value = Column(String, nullable=False, index=True)
    name = Column(String, nullable=True)  # optional contact name if found
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    entity = relationship("Entity", back_populates="contacts")


class SearchHistory(Base):
    __tablename__ = "search_history"

    id = Column(Integer, primary_key=True, index=True)
    scrape_job_id = Column(Integer, ForeignKey("scrape_jobs.id"), nullable=False)
    
    search_query = Column(String, nullable=False)
    source = Column(String, nullable=False)  # DuckDuckGo, Europages, ThomasNet, YellowPages, etc.
    results_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    scrape_job = relationship("ScrapeJob", back_populates="search_history")


class Classification(Base):
    __tablename__ = "classifications"

    id = Column(Integer, primary_key=True, index=True)
    entity_id = Column(Integer, ForeignKey("entities.id"), nullable=False)
    
    classification = Column(String, nullable=False)
    industry = Column(String, nullable=True)
    confidence = Column(Float, default=1.0)
    method = Column(String, default="rules")  # Ollama, rules
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    entity = relationship("Entity", back_populates="classifications")


class FailedUrl(Base):
    __tablename__ = "failed_urls"

    id = Column(Integer, primary_key=True, index=True)
    scrape_job_id = Column(Integer, ForeignKey("scrape_jobs.id"), nullable=False)
    
    url = Column(String, nullable=False)
    reason = Column(Text, nullable=True)
    retry_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    scrape_job = relationship("ScrapeJob", back_populates="failed_urls")
