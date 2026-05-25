import os
from pydantic_settings import BaseSettings
from typing import List, Optional

class Settings(BaseSettings):
    # App Settings
    PROJECT_NAME: str = "Bottle Lead Generator"
    API_V1_STR: str = "/api/v1"
    
    # SQLite Database Configuration
    # We will save the database file inside the backend directory.
    DATABASE_URL: str = "sqlite:///./leads.db"
    
    # Scraper & Crawler Settings
    MAX_CONCURRENT_CRAWLS: int = 5
    CRAWL_TIMEOUT: int = 30  # seconds per page
    USER_AGENT_ROTATION: bool = True
    
    # Ollama Classification Settings
    OLLAMA_HOST: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "llama3"  # Fallback to rules if llama3 is not present
    
    # Gemini API Settings (Optional cloud fallback)
    GEMINI_API_KEY: Optional[str] = None
    
    # Pre-defined user agents for rotation
    USER_AGENTS: List[str] = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:126.0) Gecko/20100101 Firefox/126.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Safari/605.1.15",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
        "Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) CriOS/125.0.6422.80 Mobile/15E148 Safari/604.1",
    ]

    class Config:
        case_sensitive = True
        env_file = ".env"

settings = Settings()
