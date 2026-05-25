import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.config import settings
from app.db.session import init_db
from app.utils import queue_manager
from app.scrapers import browser_manager
from app.api import router

logger = logging.getLogger("Main")

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle manager for FastAPI startup and shutdown routines."""
    logger.info("Initializing database and background worker services...")
    
    # Ensure data directories exist
    import os
    for path in ["./data", "./exports", "./logs", "./temp"]:
        os.makedirs(path, exist_ok=True)
        
    # Initialize database
    init_db()
    
    # Start the asyncio queue worker
    await queue_manager.start()
    
    # Start the browser manager
    await browser_manager.start()
    
    yield
    
    logger.info("Shutting down background worker and browser services...")
    # Stop background queue worker
    await queue_manager.stop()
    
    # Close browser instances
    await browser_manager.close()

app = FastAPI(
    title=settings.PROJECT_NAME,
    lifespan=lifespan,
)

# CORS configuration
# Allows requests from React/Vite development server (e.g. http://localhost:5173)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For local ease of use, allow all. Restrict in production.
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount API router
app.include_router(router, prefix=settings.API_V1_STR)

@app.get("/")
def read_root():
    return {
        "status": "online",
        "app": settings.PROJECT_NAME,
        "api_docs": "/docs"
    }
