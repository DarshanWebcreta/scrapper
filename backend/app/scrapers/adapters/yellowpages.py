import logging
import urllib.parse
from typing import Set, Optional
from bs4 import BeautifulSoup
from app.scrapers.adapters.base_adapter import BaseAdapter
from app.scrapers.base_scraper import browser_manager
from app.scrapers.adapters.duckduckgo import is_valid_company_website

logger = logging.getLogger("YellowPagesAdapter")

class YellowPagesAdapter(BaseAdapter):
    def __init__(self):
        super().__init__("YellowPages")

    async def search(self, keyword: str, country: Optional[str] = None, max_pages: int = 1) -> Set[str]:
        discovered_urls: Set[str] = set()
        location = country or "USA"
        logger.info(f"Querying Yellow Pages for: '{keyword}' in '{location}' (max pages: {max_pages})")
        
        query_encoded = urllib.parse.quote_plus(keyword)
        loc_encoded = urllib.parse.quote_plus(location)
        
        for page_idx in range(1, max_pages + 1):
            url = f"https://www.yellowpages.com/search?search_terms={query_encoded}&geo_location_terms={loc_encoded}&page={page_idx}"
            
            try:
                html, status = await browser_manager.fetch_page_content(url)
                if status != 200 or not html:
                    logger.warning(f"Yellow Pages returned status {status} or empty content.")
                    break
                    
                soup = BeautifulSoup(html, "html.parser")
                links_found = 0
                
                # In YP, website links usually have class "track-visit-website"
                for a in soup.find_all("a", class_="track-visit-website", href=True):
                    href = a["href"].strip()
                    if href.startswith("http") and is_valid_company_website(href):
                        parsed = urllib.parse.urlparse(href)
                        discovered_urls.add(f"{parsed.scheme}://{parsed.netloc}/")
                        links_found += 1
                        
                # Fallback to general external links if no track-visit-website is found
                if links_found == 0:
                    for a in soup.find_all("a", href=True):
                        href = a["href"].strip()
                        # Exclude self-links or common platforms
                        if href.startswith("http") and not any(d in href for d in ["yellowpages.com", "google.com", "facebook.com", "twitter.com", "linkedin.com"]):
                            if is_valid_company_website(href):
                                parsed = urllib.parse.urlparse(href)
                                discovered_urls.add(f"{parsed.scheme}://{parsed.netloc}/")
                                links_found += 1
                                
                logger.info(f"Yellow Pages page {page_idx}: Found {links_found} candidate domains.")
                if links_found == 0:
                    break
            except Exception as e:
                logger.warning(f"Error scraping Yellow Pages: {e}")
                break
                
        return discovered_urls
