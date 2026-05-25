import logging
import urllib.parse
import asyncio
import random
import re
from typing import Set, Optional
from bs4 import BeautifulSoup
from app.scrapers.adapters.base_adapter import BaseAdapter
from app.scrapers.base_scraper import browser_manager
from app.scrapers.adapters.duckduckgo import is_valid_company_website

logger = logging.getLogger("GoogleAdapter")

class GoogleAdapter(BaseAdapter):
    def __init__(self):
        super().__init__("Google")

    async def search(self, keyword: str, country: Optional[str] = None, max_pages: int = 1) -> Set[str]:
        discovered_urls: Set[str] = set()
        
        # Prevent double-concatenation of the country name
        if country and country.lower() not in keyword.lower():
            query = f"{keyword} in {country}"
        else:
            query = keyword
            
        # List of general web search engines to query sequentially as fallbacks
        engines = [
            {"name": "Google", "url": "https://www.google.com/search?q={query}&start={offset}", "offset_mult": 10},
            {"name": "Bing", "url": "https://www.bing.com/search?q={query}&first={offset}", "offset_mult": 10},
            {"name": "Brave", "url": "https://search.brave.com/search?q={query}&offset={offset}", "offset_mult": 1},
            {"name": "Yahoo", "url": "https://search.yahoo.com/search?p={query}&b={offset}", "offset_mult": 10}
        ]
        
        for engine in engines:
            logger.info(f"Querying {engine['name']} for: '{query}' (pages: {max_pages})")
            engine_discovered: Set[str] = set()
            
            for page_idx in range(max_pages):
                offset = page_idx * engine["offset_mult"]
                encoded_query = urllib.parse.quote_plus(query)
                search_url = engine["url"].format(query=encoded_query, offset=offset)
                
                try:
                    html_content, status = await browser_manager.fetch_page_content(search_url)
                    if status != 200 or not html_content:
                        logger.warning(f"{engine['name']} returned status {status} or empty content.")
                        break
                        
                    soup = BeautifulSoup(html_content, "html.parser")
                    page_found_count = 0
                    
                    for a in soup.find_all("a", href=True):
                        href = a["href"].strip()
                        target_url = None
                        
                        # Handle Google redirect links
                        if engine["name"] == "Google" and "/url?q=" in href:
                            try:
                                parsed_href = urllib.parse.urlparse(href)
                                qs = urllib.parse.parse_qs(parsed_href.query)
                                target_url = qs.get("q", [None])[0]
                            except Exception:
                                pass
                        
                        # Handle Yahoo redirect links
                        elif engine["name"] == "Yahoo" and "/RU=" in href:
                            try:
                                match = re.search(r'RU=([^/&]+)', href)
                                if match:
                                    target_url = urllib.parse.unquote(match.group(1))
                            except Exception:
                                pass
                                
                        # Standard link fallback
                        if not target_url and href.startswith("http"):
                            # Exclude major portals and search engine URLs
                            exclude_domains = [
                                "google.com", "gstatic.com", "youtube.com", "accounts.google.com", "support.google.com",
                                "bing.com", "microsoft.com", "live.com", "msn.com",
                                "brave.com", "yahoo.com", "yimg.com", "yahoo.co.jp",
                                "facebook.com", "linkedin.com", "twitter.com", "x.com", "instagram.com"
                            ]
                            if not any(d in href.lower() for d in exclude_domains):
                                target_url = href
                                
                        if target_url and is_valid_company_website(target_url):
                            parsed = urllib.parse.urlparse(target_url)
                            home_url = f"{parsed.scheme}://{parsed.netloc}/"
                            engine_discovered.add(home_url)
                            page_found_count += 1
                            
                    logger.info(f"{engine['name']} page {page_idx + 1}: extracted {page_found_count} domains.")
                    if page_found_count == 0:
                        break
                        
                    await asyncio.sleep(random.uniform(1.0, 2.0))
                except Exception as e:
                    logger.error(f"Error scraping {engine['name']} results: {e}")
                    break
                    
            if engine_discovered:
                logger.info(f"Success with {engine['name']}. Found {len(engine_discovered)} domains.")
                discovered_urls.update(engine_discovered)
                # Stop checking other engines since we got results!
                break
            else:
                logger.warning(f"{engine['name']} returned 0 results. Trying next engine in chain...")
                
        return discovered_urls
