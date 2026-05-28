import asyncio
import logging
from typing import Set, Dict, Any, List
from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.db import crud
from app.scrapers.query_planner import plan_search_queries
from app.scrapers.adapters import select_adapters
from app.scrapers.crawler import crawl_company_website
from app.config import settings

logger = logging.getLogger("QueueManager")

class QueueManager:
    def __init__(self):
        self.queue = asyncio.Queue()
        self.worker_task = None
        self.active_job_id = None
        self._cancel_requested = False

    async def start(self):
        """Start the background worker task."""
        if not self.worker_task:
            self.worker_task = asyncio.create_task(self._worker_loop())
            logger.info("Background queue worker started.")

    async def stop(self):
        """Stop the background worker task."""
        if self.worker_task:
            self.worker_task.cancel()
            try:
                await self.worker_task
            except asyncio.CancelledError:
                pass
            self.worker_task = None
            logger.info("Background queue worker stopped.")

    async def enqueue_query(self, job_id: int):
        """Add a scrape job to the processing queue."""
        await self.queue.put(job_id)
        logger.info(f"Enqueued scrape job #{job_id}")

    def cancel_active_job(self):
        """Flag the current active job for cancellation."""
        if self.active_job_id:
            self._cancel_requested = True
            logger.info(f"Cancellation requested for job #{self.active_job_id}")

    async def _worker_loop(self):
        while True:
            try:
                job_id = await self.queue.get()
                self.active_job_id = job_id
                self._cancel_requested = False
                
                logger.info(f"Starting processing of scrape job #{job_id}")
                await self._process_job(job_id)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in queue worker loop: {e}", exc_info=True)
            finally:
                if self.active_job_id:
                    self.queue.task_done()
                    self.active_job_id = None
                    self._cancel_requested = False

    async def _process_job(self, job_id: int):
        db: Session = SessionLocal()
        job = crud.get_scrape_job(db, job_id)
        if not job:
            logger.error(f"Scrape job #{job_id} not found in database.")
            db.close()
            return

        crud.update_scrape_job(db, job_id, status="running", progress=2.0)
        logger.info(f"Running job #{job_id}: Query='{job.query}', Countries={job.countries}, Fields={job.fields_to_extract}")
        
        try:
            # 1. AI Query Planner: generate search keywords
            crud.update_scrape_job(db, job_id, progress=5.0)
            countries_list = job.countries if isinstance(job.countries, list) else []
            keywords = await plan_search_queries(job.query, countries_list)
            
            # Save keywords back to job
            crud.update_scrape_job(db, job_id, custom_keywords=keywords)
            
            if self._cancel_requested:
                crud.update_scrape_job(db, job_id, status="cancelled", progress=100.0)
                db.close()
                return

            # 2. Select Source Adapters dynamically based on query and target countries
            countries_list = job.countries if isinstance(job.countries, list) else []
            adapters = select_adapters(job.query, countries_list)
            adapter_names = [a.name for a in adapters]
            logger.info(f"Selected adapters for job #{job_id}: {adapter_names}")
            
            # 3. Discover URLs across adapters
            crud.update_scrape_job(db, job_id, progress=10.0)
            discovered_urls: Set[str] = set()
            
            # Limit keyword queries to the top 3 variations to prevent wasteful long runs
            keywords_to_query = keywords[:3]
            
            # Query sequentially per adapter/keyword to be polite and avoid blocks
            for adapter in adapters:
                if self._cancel_requested or len(discovered_urls) >= 20:
                    break
                for kw in keywords_to_query:
                    if self._cancel_requested or len(discovered_urls) >= 20:
                        break
                    try:
                        logger.info(f"Running search: Adapter={adapter.name}, Keyword='{kw}'")
                        # Run discovery
                        for country in (countries_list or [None]):
                            if self._cancel_requested or len(discovered_urls) >= 20:
                                break
                            urls = await adapter.search(kw, country, max_pages=job.max_pages or 1)
                            if urls:
                                discovered_urls.update(urls)
                                # Log history
                                crud.create_search_history(db, job_id, f"{kw} ({country or 'Global'})", adapter.name, len(urls))
                    except Exception as e:
                        logger.warning(f"Adapter {adapter.name} failed for query '{kw}': {e}")
                    
                    # Check early stopping condition
                    if len(discovered_urls) >= 20:
                        logger.info(f"Early stopping discovery phase: already found {len(discovered_urls)} target URLs.")
                        break
                        
                    # polite wait
                    await asyncio.sleep(1.0)
            
            if self._cancel_requested:
                crud.update_scrape_job(db, job_id, status="cancelled", progress=100.0)
                db.close()
                return

            total_discovered = len(discovered_urls)
            crud.update_scrape_job(db, job_id, total_discovered=total_discovered, progress=25.0)
            
            if total_discovered == 0:
                logger.info("No URLs discovered for this scrape run.")
                crud.update_scrape_job(db, job_id, status="completed", progress=100.0)
                db.close()
                return

            # 4. Crawling & Extraction Phase
            logger.info(f"Discovered {total_discovered} domains. Initiating crawlers...")
            
            crawled_count = 0
            lead_count = 0
            
            # Concurrency limit from job configuration
            concurrency_limit = job.concurrency or settings.MAX_CONCURRENT_CRAWLS
            semaphore = asyncio.Semaphore(concurrency_limit)
            
            async def crawl_task(url: str):
                nonlocal crawled_count, lead_count
                
                async with semaphore:
                    if self._cancel_requested:
                        return
                    
                    try:
                        # Crawl website
                        res = await crawl_company_website(
                            website_url=url,
                            scrape_job_id=job_id,
                            fields_to_extract=job.fields_to_extract,
                            source="Discovery Platform"
                        )
                        
                        if res:
                            entity_data = res["entity"]
                            contacts_list = res["contacts"]
                            
                            # Deduplication check
                            domain = entity_data["domain"]
                            emails = [c["value"] for c in contacts_list if c["type"] == "email"]
                            phones = [c["value"] for c in contacts_list if c["type"] == "phone"]
                            
                            task_db = SessionLocal()
                            try:
                                duplicate = crud.get_entity_by_domain_or_contact(task_db, domain, emails, phones)
                                if duplicate:
                                    logger.info(f"Ignoring duplicate entity: domain='{domain}'")
                                else:
                                    crud.create_entity(task_db, entity_data, contacts_list)
                                    lead_count += 1
                                    logger.info(f"Saved entity: '{entity_data['company_name']}'")
                            finally:
                                task_db.close()
                                
                    except Exception as e:
                        logger.error(f"Failed crawling website {url}: {e}")
                        # Log fail details
                        task_db = SessionLocal()
                        try:
                            crud.create_failed_url(task_db, job_id, url, str(e))
                        finally:
                            task_db.close()
                    finally:
                        crawled_count += 1
                        # Update progress metrics
                        progress = 25.0 + (70.0 * (crawled_count / total_discovered))
                        if self._cancel_requested:
                            progress = 100.0
                        crud.update_scrape_job(
                            db,
                            job_id,
                            total_crawled=crawled_count,
                            total_leads=lead_count,
                            progress=round(progress, 1)
                        )

            # Build tasks list
            tasks = [crawl_task(url) for url in discovered_urls]
            
            # Execute tasks in chunks matching concurrency limits
            for chunk_idx in range(0, len(tasks), concurrency_limit):
                if self._cancel_requested:
                    break
                chunk = tasks[chunk_idx : chunk_idx + concurrency_limit]
                await asyncio.gather(*chunk, return_exceptions=True)
                
            if self._cancel_requested:
                logger.info(f"Scrape job #{job_id} cancelled by user request.")
                crud.update_scrape_job(db, job_id, status="cancelled", progress=100.0)
            else:
                logger.info(f"Finished job #{job_id}. Discovered={total_discovered}, Crawled={crawled_count}, Saved Entities={lead_count}")
                crud.update_scrape_job(db, job_id, status="completed", progress=100.0)

        except Exception as e:
            logger.error(f"Error executing scrape job #{job_id}: {e}", exc_info=True)
            crud.update_scrape_job(db, job_id, status="failed", progress=100.0, error_message=str(e))
        finally:
            db.close()

# Singleton Queue Manager
queue_manager = QueueManager()
