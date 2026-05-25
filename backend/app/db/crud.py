from sqlalchemy.orm import Session
from sqlalchemy import func, or_
from datetime import datetime
from typing import List, Optional, Dict, Any
from app.db.models import ScrapeJob, Entity, Contact, SearchHistory, Classification, FailedUrl, ExtractionSchema

# --- ScrapeJob CRUD ---

def get_scrape_job(db: Session, job_id: int) -> Optional[ScrapeJob]:
    return db.query(ScrapeJob).filter(ScrapeJob.id == job_id).first()

def get_scrape_jobs(db: Session, skip: int = 0, limit: int = 100) -> List[ScrapeJob]:
    return db.query(ScrapeJob).order_by(ScrapeJob.created_at.desc()).offset(skip).limit(limit).all()

def create_scrape_job(
    db: Session, 
    query: str, 
    countries: List[str] = None, 
    industries: List[str] = None, 
    fields_to_extract: List[str] = None, 
    max_pages: int = 5,
    concurrency: int = 5,
    export_format: str = "csv"
) -> ScrapeJob:
    db_job = ScrapeJob(
        query=query,
        countries=countries or [],
        industries=industries or [],
        custom_keywords=[],
        fields_to_extract=fields_to_extract or ["company_name", "website", "emails", "phones"],
        max_pages=max_pages,
        concurrency=concurrency,
        export_format=export_format,
        status="pending",
        total_discovered=0,
        total_crawled=0,
        total_leads=0,
        progress=0.0
    )
    db.add(db_job)
    db.commit()
    db.refresh(db_job)
    
    # Save extraction schema fields
    if fields_to_extract:
        for field in fields_to_extract:
            schema_item = ExtractionSchema(
                scrape_job_id=db_job.id,
                field_name=field,
                field_type="email" if "email" in field.lower() else "phone" if "phone" in field.lower() or "whatsapp" in field.lower() else "text"
            )
            db.add(schema_item)
        db.commit()
        db.refresh(db_job)
        
    return db_job

def update_scrape_job(db: Session, job_id: int, **kwargs) -> Optional[ScrapeJob]:
    db_job = get_scrape_job(db, job_id)
    if db_job:
        for key, value in kwargs.items():
            if hasattr(db_job, key):
                setattr(db_job, key, value)
        db_job.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(db_job)
    return db_job

def delete_scrape_job(db: Session, job_id: int) -> bool:
    db_job = get_scrape_job(db, job_id)
    if db_job:
        db.delete(db_job)
        db.commit()
        return True
    return False


# --- Entity (Lead) & Contact CRUD ---

def get_entity(db: Session, entity_id: int) -> Optional[Entity]:
    return db.query(Entity).filter(Entity.id == entity_id).first()

def get_entity_by_domain_or_contact(db: Session, domain: str, emails_list: List[str], phones_list: List[str]) -> Optional[Entity]:
    """Check for duplicate entities by domain, or email/phone contact values."""
    if not domain:
        return None
        
    # 1. Check domain
    entity = db.query(Entity).filter(Entity.domain == domain).first()
    if entity:
        return entity
        
    # 2. Check email duplicates
    for email in emails_list:
        if email:
            contact = db.query(Contact).filter(Contact.type == "email", Contact.value == email).first()
            if contact:
                return db.query(Entity).filter(Entity.id == contact.entity_id).first()
                
    # 3. Check phone duplicates
    for phone in phones_list:
        if phone:
            contact = db.query(Contact).filter(Contact.type == "phone", Contact.value == phone).first()
            if contact:
                return db.query(Entity).filter(Entity.id == contact.entity_id).first()
                
    return None

def create_entity(db: Session, entity_data: Dict[str, Any], contacts: List[Dict[str, Any]] = None) -> Entity:
    db_entity = Entity(
        scrape_job_id=entity_data.get("scrape_job_id"),
        company_name=entity_data.get("company_name"),
        website=entity_data.get("website"),
        domain=entity_data.get("domain"),
        description=entity_data.get("description"),
        country=entity_data.get("country"),
        address=entity_data.get("address"),
        classification=entity_data.get("classification", "unknown"),
        industry=entity_data.get("industry"),
        source=entity_data.get("source"),
        contact_page=entity_data.get("contact_page"),
        status=entity_data.get("status", "crawled"),
        extracted_data=entity_data.get("extracted_data", {})
    )
    db.add(db_entity)
    db.commit()
    db.refresh(db_entity)
    
    # Save contacts
    if contacts:
        for c in contacts:
            db_contact = Contact(
                entity_id=db_entity.id,
                type=c.get("type"),
                value=c.get("value"),
                name=c.get("name")
            )
            db.add(db_contact)
        db.commit()
        db.refresh(db_entity)
        
    return db_entity

def update_entity(db: Session, entity_id: int, **kwargs) -> Optional[Entity]:
    db_entity = get_entity(db, entity_id)
    if db_entity:
        for key, value in kwargs.items():
            if hasattr(db_entity, key):
                setattr(db_entity, key, value)
        db.commit()
        db.refresh(db_entity)
    return db_entity

def get_entities(
    db: Session,
    job_id: Optional[int] = None,
    search: Optional[str] = None,
    country: Optional[str] = None,
    classification: Optional[str] = None,
    industry: Optional[str] = None,
    skip: int = 0,
    limit: int = 100
) -> List[Entity]:
    q = db.query(Entity)
    
    if job_id is not None:
        q = q.filter(Entity.scrape_job_id == job_id)
    if search:
        search_filter = f"%{search}%"
        # Match name, domain, description, address, or classifications
        q = q.filter(
            or_(
                Entity.company_name.like(search_filter),
                Entity.domain.like(search_filter),
                Entity.description.like(search_filter),
                Entity.address.like(search_filter),
                Entity.industry.like(search_filter)
            )
        )
    if country:
        q = q.filter(Entity.country.ilike(f"%{country}%"))
    if classification:
        q = q.filter(Entity.classification == classification)
    if industry:
        q = q.filter(Entity.industry.ilike(f"%{industry}%"))
        
    return q.order_by(Entity.created_at.desc()).offset(skip).limit(limit).all()

def count_entities(
    db: Session,
    job_id: Optional[int] = None,
    search: Optional[str] = None,
    country: Optional[str] = None,
    classification: Optional[str] = None,
    industry: Optional[str] = None
) -> int:
    q = db.query(func.count(Entity.id))
    
    if job_id is not None:
        q = q.filter(Entity.scrape_job_id == job_id)
    if search:
        search_filter = f"%{search}%"
        q = q.filter(
            or_(
                Entity.company_name.like(search_filter),
                Entity.domain.like(search_filter),
                Entity.description.like(search_filter),
                Entity.address.like(search_filter),
                Entity.industry.like(search_filter)
            )
        )
    if country:
        q = q.filter(Entity.country.ilike(f"%{country}%"))
    if classification:
        q = q.filter(Entity.classification == classification)
    if industry:
        q = q.filter(Entity.industry.ilike(f"%{industry}%"))
        
    return q.scalar() or 0


# --- Search History CRUD ---

def create_search_history(db: Session, job_id: int, search_query: str, source: str, results_count: int = 0) -> SearchHistory:
    db_history = SearchHistory(
        scrape_job_id=job_id,
        search_query=search_query,
        source=source,
        results_count=results_count
    )
    db.add(db_history)
    db.commit()
    db.refresh(db_history)
    return db_history


# --- Classification CRUD ---

def create_classification(db: Session, entity_id: int, classification: str, industry: Optional[str] = None, confidence: float = 1.0, method: str = "rules") -> Classification:
    db_classification = Classification(
        entity_id=entity_id,
        classification=classification,
        industry=industry,
        confidence=confidence,
        method=method
    )
    db.add(db_classification)
    db.commit()
    db.refresh(db_classification)
    return db_classification


# --- Failed URLs CRUD ---

def get_failed_urls(db: Session, job_id: int) -> List[FailedUrl]:
    return db.query(FailedUrl).filter(FailedUrl.scrape_job_id == job_id).all()

def create_failed_url(db: Session, job_id: int, url: str, reason: Optional[str] = None) -> FailedUrl:
    db_failed = FailedUrl(
        scrape_job_id=job_id,
        url=url,
        reason=reason,
        retry_count=0
    )
    db.add(db_failed)
    db.commit()
    db.refresh(db_failed)
    return db_failed

def clear_failed_urls(db: Session, job_id: int):
    db.query(FailedUrl).filter(FailedUrl.scrape_job_id == job_id).delete()
    db.commit()


# --- Dashboard Stats Aggregation ---

def get_dashboard_stats(db: Session) -> Dict[str, Any]:
    total_searches = db.query(func.count(ScrapeJob.id)).scalar() or 0
    total_leads = db.query(func.count(Entity.id)).scalar() or 0
    
    # Extract unique email count from contacts table
    distinct_emails = db.query(func.count(func.distinct(Contact.value))).filter(Contact.type == "email").scalar() or 0
    
    # Extract unique phone count
    distinct_phones = db.query(func.count(func.distinct(Contact.value))).filter(Contact.type.in_(["phone", "whatsapp"])).scalar() or 0
    
    # Classifications count
    class_counts = db.query(Entity.classification, func.count(Entity.id)).group_by(Entity.classification).all()
    classifications = {cls or "unknown": count for cls, count in class_counts}
    
    return {
        "total_searches": total_searches,
        "total_leads": total_leads,
        "total_emails": distinct_emails,
        "total_phones": distinct_phones,
        "classifications": classifications
    }
