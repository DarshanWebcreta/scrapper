import logging
import urllib.parse
from typing import Set, Optional
from bs4 import BeautifulSoup
from app.scrapers.adapters.base_adapter import BaseAdapter
from app.scrapers.base_scraper import browser_manager
from app.scrapers.adapters.duckduckgo import is_valid_company_website

logger = logging.getLogger("ThomasNetAdapter")

class ThomasNetAdapter(BaseAdapter):
    def __init__(self):
        super().__init__("ThomasNet")

    async def search(self, keyword: str, country: Optional[str] = None, max_pages: int = 1) -> Set[str]:
        discovered_urls: Set[str] = set()
        logger.info(f"Querying ThomasNet for: '{keyword}' (max pages: {max_pages})")
        
        query_encoded = urllib.parse.quote_plus(keyword)
        
        for page_idx in range(1, max_pages + 1):
            # ThomasNet search structure
            url = f"https://www.thomasnet.com/search.html?what={query_encoded}&pg={page_idx}"
            if country:
                url += f"&cov={urllib.parse.quote_plus(country)}"
                
            try:
                html, status = await browser_manager.fetch_page_content(url)
                if status != 200 or not html:
                    logger.warning(f"ThomasNet returned status {status} or empty content.")
                    break
                    
                soup = BeautifulSoup(html, "html.parser")
                links_found = 0
                for a in soup.find_all("a", href=True):
                    href = a["href"].strip()
                    # Look for external company website links
                    if href.startswith("http") and not any(d in href for d in ["thomasnet", "google", "facebook", "linkedin", "twitter", "instagram"]):
                        if is_valid_company_website(href):
                            parsed = urllib.parse.urlparse(href)
                            discovered_urls.add(f"{parsed.scheme}://{parsed.netloc}/")
                            links_found += 1
                            
                    # Scan for links with labels like "Website" or attributes
                    if "website" in a.get_text().lower() or a.get("title", "").lower() == "website":
                        if href.startswith("http") and is_valid_company_website(href):
                            parsed = urllib.parse.urlparse(href)
                            discovered_urls.add(f"{parsed.scheme}://{parsed.netloc}/")
                            links_found += 1
                            
                logger.info(f"ThomasNet page {page_idx}: Found {links_found} candidate domains.")
                if links_found == 0:
                    break
            except Exception as e:
                logger.warning(f"Error scraping ThomasNet: {e}")
                break
                
        return discovered_urls
