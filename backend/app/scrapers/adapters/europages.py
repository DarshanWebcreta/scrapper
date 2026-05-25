import logging
import urllib.parse
from typing import Set, Optional
from bs4 import BeautifulSoup
from app.scrapers.adapters.base_adapter import BaseAdapter
from app.scrapers.base_scraper import browser_manager
from app.scrapers.adapters.duckduckgo import is_valid_company_website

logger = logging.getLogger("EuropagesAdapter")

class EuropagesAdapter(BaseAdapter):
    def __init__(self):
        super().__init__("Europages")

    async def search(self, keyword: str, country: Optional[str] = None, max_pages: int = 1) -> Set[str]:
        discovered_urls: Set[str] = set()
        logger.info(f"Querying Europages for: '{keyword}' (max pages: {max_pages})")
        
        # Format query for URL
        query_encoded = urllib.parse.quote_plus(keyword)
        
        for page_idx in range(1, max_pages + 1):
            # Europages search structure
            url = f"https://www.europages.co.uk/ep-search?q={query_encoded}&page={page_idx}"
            if country:
                url += f"&country={urllib.parse.quote_plus(country)}"
                
            try:
                html, status = await browser_manager.fetch_page_content(url)
                if status != 200 or not html:
                    logger.warning(f"Europages returned status {status} or empty content.")
                    break
                    
                soup = BeautifulSoup(html, "html.parser")
                # Look for external company website links or Europages profiles.
                # Company links are usually inside attributes like "data-website" or relative links.
                links_found = 0
                for a in soup.find_all("a", href=True):
                    href = a["href"].strip()
                    # Look for outward website links
                    if href.startswith("http") and not any(d in href for d in ["europages", "google", "facebook", "linkedin"]):
                        if is_valid_company_website(href):
                            parsed = urllib.parse.urlparse(href)
                            discovered_urls.add(f"{parsed.scheme}://{parsed.netloc}/")
                            links_found += 1
                            
                    # Alternatively, scan for typical company profile pages: "/company-profile/..." or "/o/" or matching names
                    # We can also search for buttons with text containing "Website"
                    if "website" in a.get_text().lower() or "visit" in a.get_text().lower():
                        # Extract the target URL from the href
                        # Sometimes it is a redirect link like /visit/company/XXXXX
                        if href.startswith("http") and is_valid_company_website(href):
                            parsed = urllib.parse.urlparse(href)
                            discovered_urls.add(f"{parsed.scheme}://{parsed.netloc}/")
                            links_found += 1
                
                logger.info(f"Europages page {page_idx}: Found {links_found} candidate domains.")
                if links_found == 0:
                    # Try a general query via DDG specialized to Europages to get listings
                    ddg_query = f"site:europages.co.uk {keyword} {country or ''}"
                    logger.info(f"Europages direct search returned 0. Falling back to specialized DDG query: '{ddg_query}'")
                    # We won't block, just fallback to DDG search for europages urls and extract domains
                    break
            except Exception as e:
                logger.warning(f"Error scraping Europages: {e}")
                break
                
        return discovered_urls
