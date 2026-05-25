import asyncio
import csv
import json
import logging
from io import StringIO, BytesIO
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from fastapi.responses import StreamingResponse, JSONResponse
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
import openpyxl

from app.db.session import get_db, SessionLocal
from app.db import crud
from app.db.models import Entity, ScrapeJob
from app.utils.logger import register_log_listener, unregister_log_listener, get_recent_logs
from app.utils.queue_manager import queue_manager

logger = logging.getLogger("APIRoutes")
router = APIRouter()

def serialize_entity(entity: Entity) -> Dict[str, Any]:
    """Helper to serialize Entity SQLAlchemy model to dict, flattening contact details."""
    emails = []
    phones = []
    whatsapps = []
    linkedin = None
    facebook = None
    instagram = None
    twitter = None
    youtube = None
    
    for contact in entity.contacts:
        if contact.type == "email":
            emails.append(contact.value)
        elif contact.type == "phone":
            phones.append(contact.value)
        elif contact.type == "whatsapp":
            whatsapps.append(contact.value)
        elif contact.type == "linkedin":
            linkedin = contact.value
        elif contact.type == "facebook":
            facebook = contact.value
        elif contact.type == "instagram":
            instagram = contact.value
        elif contact.type == "twitter":
            twitter = contact.value
        elif contact.type == "youtube":
            youtube = contact.value
            
    res = {
        "id": entity.id,
        "scrape_job_id": entity.scrape_job_id,
        "company_name": entity.company_name,
        "website": entity.website,
        "domain": entity.domain,
        "description": entity.description,
        "country": entity.country,
        "address": entity.address,
        "classification": entity.classification,
        "industry": entity.industry,
        "source": entity.source,
        "contact_page": entity.contact_page,
        "status": entity.status,
        "created_at": entity.created_at.isoformat() if entity.created_at else None,
        
        # Flattened contacts
        "emails": ",".join(emails) if emails else None,
        "phones": ",".join(phones) if phones else None,
        "whatsapp": ",".join(whatsapps) if whatsapps else None,
        "linkedin": linkedin,
        "facebook": facebook,
        "instagram": instagram,
        "twitter": twitter,
        "youtube": youtube
    }
    
    # Merge custom extracted fields
    if entity.extracted_data:
        for k, v in entity.extracted_data.items():
            res[k] = v
            
    return res


# --- ScrapeJob Routes ---

@router.post("/queries")  # Mapping frontend POST /queries to jobs creation
async def create_job(
    payload: dict,
    db: Session = Depends(get_db)
):
    query = payload.get("keyword") or payload.get("query")
    countries = payload.get("countries")
    # Adapt single country input if coming from old forms
    if not countries and payload.get("country"):
        countries = [payload.get("country")]
        
    industries = payload.get("industries") or []
    fields = payload.get("fields") or ["company_name", "website", "emails", "phones", "address"]
    max_pages = payload.get("max_pages", 3)
    concurrency = payload.get("concurrency", 5)
    export_format = payload.get("export_format", "csv")
    
    if not query:
        raise HTTPException(status_code=400, detail="Query/keyword is required.")
        
    db_job = crud.create_scrape_job(
        db, 
        query=query, 
        countries=countries, 
        industries=industries,
        fields_to_extract=fields,
        max_pages=max_pages,
        concurrency=concurrency,
        export_format=export_format
    )
    
    # Queue the job execution
    await queue_manager.enqueue_query(db_job.id)
    
    return db_job

@router.get("/queries")  # Mapping frontend GET /queries to list jobs
def list_jobs(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    return crud.get_scrape_jobs(db, skip=skip, limit=limit)

@router.get("/queries/{query_id}")  # Mapping frontend GET /queries/{id} to get job
def get_job(
    query_id: int,
    db: Session = Depends(get_db)
):
    db_job = crud.get_scrape_job(db, query_id)
    if not db_job:
        raise HTTPException(status_code=404, detail="Scrape job not found")
    return db_job

@router.post("/queries/{query_id}/cancel")  # Mapping frontend POST /queries/{id}/cancel to cancel job
def cancel_job(
    query_id: int,
    db: Session = Depends(get_db)
):
    db_job = crud.get_scrape_job(db, query_id)
    if not db_job:
        raise HTTPException(status_code=404, detail="Scrape job not found")
        
    if db_job.status == "running":
        queue_manager.cancel_active_job()
        crud.update_scrape_job(db, query_id, status="cancelled")
        return {"status": "Cancellation requested"}
    elif db_job.status == "pending":
        crud.update_scrape_job(db, query_id, status="cancelled")
        return {"status": "Cancelled pending search"}
        
    return {"status": f"Job is already in {db_job.status} state."}

@router.delete("/queries/{query_id}")  # Mapping frontend DELETE /queries/{id} to delete job
def delete_job(
    query_id: int,
    db: Session = Depends(get_db)
):
    success = crud.delete_scrape_job(db, query_id)
    if not success:
        raise HTTPException(status_code=404, detail="Scrape job not found")
    return {"status": "Deleted successfully"}

@router.post("/queries/{query_id}/retry")
async def retry_failed_urls(
    query_id: int,
    db: Session = Depends(get_db)
):
    """Gathers failed URLs for a job and submits them for re-crawling."""
    db_job = crud.get_scrape_job(db, query_id)
    if not db_job:
        raise HTTPException(status_code=404, detail="Scrape job not found")
        
    failed = crud.get_failed_urls(db, query_id)
    if not failed:
        return {"status": "No failed URLs to retry"}
        
    # Extract URLs
    urls_to_retry = [f.url for f in failed]
    
    # Delete failure logs
    crud.clear_failed_urls(db, query_id)
    
    # Update job stats
    crud.update_scrape_job(
        db, 
        query_id, 
        status="pending", 
        progress=0.0, 
        total_discovered=len(urls_to_retry), 
        total_crawled=0
    )
    
    # Submit job for execution in background
    await queue_manager.enqueue_query(query_id)
    
    return {"status": f"Re-enqueued job with {len(urls_to_retry)} failed URLs."}


# --- Entity (Lead) Routes ---

@router.get("/leads")
def list_leads(
    query_id: Optional[int] = Query(None, alias="query_id"),
    search: Optional[str] = None,
    country: Optional[str] = None,
    classification: Optional[str] = None,
    industry: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    entities = crud.get_entities(
        db, 
        job_id=query_id, 
        search=search, 
        country=country, 
        classification=classification, 
        industry=industry,
        skip=skip, 
        limit=limit
    )
    total = crud.count_entities(
        db, 
        job_id=query_id, 
        search=search, 
        country=country, 
        classification=classification,
        industry=industry
    )
    
    serialized = [serialize_entity(e) for e in entities]
    
    return {
        "leads": serialized,
        "total": total,
        "skip": skip,
        "limit": limit
    }

@router.get("/leads/export")
def export_leads(
    query_id: Optional[int] = Query(None, alias="query_id"),
    search: Optional[str] = None,
    country: Optional[str] = None,
    classification: Optional[str] = None,
    industry: Optional[str] = None,
    format: str = "csv",
    db: Session = Depends(get_db)
):
    """Exports lead records matching filters to CSV, JSON, or XLSX format."""
    entities = crud.get_entities(
        db, 
        job_id=query_id, 
        search=search, 
        country=country, 
        classification=classification, 
        industry=industry,
        skip=0, 
        limit=20000
    )
    
    serialized = [serialize_entity(e) for e in entities]
    
    # Collect all available fields (standard + custom fields found)
    headers = [
        "company_name", "website", "domain", "description", "emails", 
        "phones", "whatsapp", "linkedin", "facebook", "instagram", "twitter", 
        "youtube", "country", "address", "classification", "industry", "source"
    ]
    
    # Find any custom keys in serialized data
    for item in serialized:
        for key in item.keys():
            if key not in headers and key != "id" and key != "scrape_job_id" and key != "status" and key != "created_at":
                headers.append(key)
                
    # --- CSV Export ---
    if format.lower() == "csv":
        output = StringIO()
        writer = csv.writer(output)
        writer.writerow(headers)
        
        for lead in serialized:
            row = [lead.get(h) or "" for h in headers]
            writer.writerow(row)
            
        output.seek(0)
        filename = f"leads_export_{query_id or 'all'}.csv"
        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
        
    # --- JSON Export ---
    elif format.lower() == "json":
        json_str = json.dumps(serialized, indent=2)
        filename = f"leads_export_{query_id or 'all'}.json"
        return StreamingResponse(
            iter([json_str]),
            media_type="application/json",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
        
    # --- XLSX Export (Excel) ---
    elif format.lower() in ["xlsx", "excel"]:
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Extracted Leads"
        
        # Write headers
        ws.append(headers)
        
        # Write rows
        for lead in serialized:
            row = [str(lead.get(h)) if lead.get(h) is not None else "" for h in headers]
            ws.append(row)
            
        output = BytesIO()
        wb.save(output)
        output.seek(0)
        
        filename = f"leads_export_{query_id or 'all'}.xlsx"
        return StreamingResponse(
            output,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
        
    else:
        raise HTTPException(status_code=400, detail="Invalid export format. Choose csv, json, or excel.")


# --- Dashboard Stats ---

@router.get("/stats")
def get_stats(db: Session = Depends(get_db)):
    return crud.get_dashboard_stats(db)


# --- Live Logs Streaming (SSE) ---

@router.get("/logs/stream")
async def stream_logs():
    """SSE endpoint streaming live logger messages."""
    
    async def log_generator():
        queue = asyncio.Queue()
        
        def listener_cb(message: str):
            queue.put_nowait(message)
            
        register_log_listener(listener_cb)
        logger.debug("New SSE log client connected.")
        
        try:
            # 1. Stream log history first
            for historical_log in get_recent_logs():
                yield f"data: {historical_log}\n\n"
                
            # 2. Stream new logs in real-time
            while True:
                msg = await queue.get()
                yield f"data: {msg}\n\n"
                queue.task_done()
                
        except asyncio.CancelledError:
            logger.debug("SSE log client disconnected.")
        finally:
            unregister_log_listener(listener_cb)
            
    return StreamingResponse(log_generator(), media_type="text/event-stream")
