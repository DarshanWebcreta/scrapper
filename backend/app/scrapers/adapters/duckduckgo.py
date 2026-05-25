import logging
import urllib.parse
import asyncio
import random
from typing import Set, Optional
from bs4 import BeautifulSoup
from app.scrapers.adapters.base_adapter import BaseAdapter
from app.scrapers.base_scraper import browser_manager

logger = logging.getLogger("DuckDuckGoAdapter")

DOMAINS_BLACKLIST = {
    "google.com", "bing.com", "yahoo.com", "duckduckgo.com", "brave.com",
    "wikipedia.org", "wiktionary.org", "amazon.com", "ebay.com", "alibaba.com",
    "youtube.com", "facebook.com", "linkedin.com", "twitter.com", "x.com",
    "instagram.com", "pinterest.com", "reddit.com", "yelp.com", "tripadvisor.com",
    "yellowpages.com", "thomasnet.com", "europages.com", "indiamart.com", 
    "kompass.com", "made-in-china.com", "globalsources.com", "tradeindia.com",
    "glassdoor.com", "indeed.com", "crunchbase.com", "mapquest.com", "local.com"
}

def clean_url_from_ddg_redirect(href: str) -> Optional[str]:
    """Extract actual destination from DDG redirect parameters."""
    if not href:
        return None
    if "uddg=" in href:
        try:
            parsed = urllib.parse.urlparse(href)
            query_params = urllib.parse.parse_qs(parsed.query)
            target = query_params.get("uddg", [None])[0]
            return target
        except Exception:
            pass
    if href.startswith("http://") or href.startswith("https://"):
        return href
    return None

def is_valid_company_website(url: str) -> bool:
    """Filter out search engines, social media, and direct listing directories."""
    if not url:
        return False
    try:
        parsed = urllib.parse.urlparse(url)
        domain = (parsed.netloc or parsed.path).lower()
        if domain.startswith("www."):
            domain = domain[4:]
        if domain in DOMAINS_BLACKLIST:
            return False
        for blacklisted in DOMAINS_BLACKLIST:
            if domain == blacklisted or domain.endswith("." + blacklisted):
                return False
        return True
    except Exception:
        return False

class DuckDuckGoAdapter(BaseAdapter):
    def __init__(self):
        super().__init__("DuckDuckGo")

    async def search(self, keyword: str, country: Optional[str] = None, max_pages: int = 1) -> Set[str]:
        discovered_urls: Set[str] = set()
        
        # Prevent double-concatenation of the country name
        if country and country.lower() not in keyword.lower():
            query = f"{keyword} in {country}"
        else:
            query = keyword
            
        logger.info(f"Querying DuckDuckGo: '{query}' (pages: {max_pages})")
        
        for page_idx in range(max_pages):
            offset = page_idx * 30
            encoded_query = urllib.parse.quote_plus(query)
            search_url = f"https://html.duckduckgo.com/html/?q={encoded_query}"
            if offset > 0:
                search_url += f"&s={offset}"
                
            try:
                html_content, status = await browser_manager.fetch_page_content(search_url)
                if status != 200 or not html_content:
                    logger.warning(f"Failed to fetch DDG page (status: {status})")
                    break
                    
                soup = BeautifulSoup(html_content, "html.parser")
                result_links = soup.find_all("a", class_="result__url")
                if not result_links:
                    result_links = soup.find_all("a", href=True)
                    
                page_found_count = 0
                for link in result_links:
                    href = link.get("href", "")
                    target_url = clean_url_from_ddg_redirect(href)
                    
                    if target_url and is_valid_company_website(target_url):
                        parsed = urllib.parse.urlparse(target_url)
                        home_url = f"{parsed.scheme}://{parsed.netloc}/"
                        discovered_urls.add(home_url)
                        page_found_count += 1
                        
                logger.info(f"DDG page {page_idx + 1}: extracted {page_found_count} domains.")
                if page_found_count == 0:
                    break
                await asyncio.sleep(random.uniform(1.0, 2.0))
            except Exception as e:
                logger.error(f"Error scraping DDG results: {e}")
                break
                
        return discovered_urls
