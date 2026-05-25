import logging
import urllib.parse
from typing import Set, Optional
from bs4 import BeautifulSoup
from app.scrapers.adapters.base_adapter import BaseAdapter
from app.scrapers.base_scraper import browser_manager
from app.scrapers.adapters.duckduckgo import is_valid_company_website

logger = logging.getLogger("IndiaMartAdapter")

class IndiaMartAdapter(BaseAdapter):
    def __init__(self):
        super().__init__("IndiaMART")

    async def search(self, keyword: str, country: Optional[str] = None, max_pages: int = 1) -> Set[str]:
        discovered_urls: Set[str] = set()
        logger.info(f"Querying IndiaMART for: '{keyword}' (max pages: {max_pages})")
        
        query_encoded = urllib.parse.quote_plus(keyword)
        
        for page_idx in range(1, max_pages + 1):
            url = f"https://dir.indiamart.com/search.mp?ss={query_encoded}"
            if page_idx > 1:
                # IndiaMART handles pagination in search query, but search.mp works nicely with simple queries
                break
                
            try:
                html, status = await browser_manager.fetch_page_content(url)
                if status != 200 or not html:
                    logger.warning(f"IndiaMART returned status {status} or empty content.")
                    break
                    
                soup = BeautifulSoup(html, "html.parser")
                links_found = 0
                for a in soup.find_all("a", href=True):
                    href = a["href"].strip()
                    # Indiamart vendors have websites under *.indiamart.com or custom domains
                    if href.startswith("http") and not any(d in href for d in ["google", "facebook", "linkedin", "twitter", "youtube"]):
                        # Keep custom websites
                        if not "indiamart.com" in href:
                            if is_valid_company_website(href):
                                parsed = urllib.parse.urlparse(href)
                                discovered_urls.add(f"{parsed.scheme}://{parsed.netloc}/")
                                links_found += 1
                        else:
                            # Indiamart listing website links often have parameter fields or custom paths
                            # e.g., https://www.indiamart.com/company/1234567/ or vendor sites
                            # We can capture these if they represent company domains
                            pass
                            
                logger.info(f"IndiaMART: Found {links_found} candidate domains.")
            except Exception as e:
                logger.warning(f"Error scraping IndiaMART: {e}")
                break
                
        return discovered_urls
