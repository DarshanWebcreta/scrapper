import logging
import asyncio
import urllib.parse
from bs4 import BeautifulSoup
from typing import List, Set, Optional
from app.scrapers.base_scraper import browser_manager

logger = logging.getLogger("SearchScraper")

# List of industries requested by the user
INDUSTRIES = [
    "beverage manufacturing",
    "breweries",
    "water bottling",
    "soft drink manufacturing",
    "coca-cola bottling",
    "pepsi bottling",
    "juice manufacturers",
    "bottle manufacturers",
    "packaging manufacturers",
    "PET bottle manufacturers",
    "glass bottle manufacturers"
]

# Blacklist of major domains to filter out from discovered company websites
DOMAINS_BLACKLIST = {
    "google.com", "bing.com", "yahoo.com", "duckduckgo.com", "brave.com",
    "wikipedia.org", "wiktionary.org", "amazon.com", "ebay.com", "alibaba.com",
    "youtube.com", "facebook.com", "linkedin.com", "twitter.com", "x.com",
    "instagram.com", "pinterest.com", "reddit.com", "yelp.com", "tripadvisor.com",
    "yellowpages.com", "thomasnet.com", "europages.com", "indiamart.com", 
    "kompass.com", "made-in-china.com", "globalsources.com", "tradeindia.com",
    "glassdoor.com", "indeed.com", "crunchbase.com", "mapquest.com", "local.com"
}

def generate_search_keywords(user_keyword: str, country: Optional[str] = None) -> List[str]:
    """
    Generate dynamic search keywords.
    If a country is provided, uses templates like '{industry keyword} in {country}'
    for all pre-defined industries, plus the user's keyword.
    """
    keywords = []
    
    # Clean inputs
    user_keyword = user_keyword.strip() if user_keyword else "bottle manufacturer"
    country_clean = country.strip() if country else ""
    
    if country_clean and country_clean.lower() != "global":
        # 1. Main user query with country
        keywords.append(f"{user_keyword} in {country_clean}")
        
        # 2. Template combination for all default industries
        for industry in INDUSTRIES:
            keywords.append(f"{industry} in {country_clean}")
    else:
        # No country filter: just search the user's primary keyword
        keywords.append(user_keyword)
        
    return keywords

def clean_url_from_ddg_redirect(href: str) -> Optional[str]:
    """
    Extract the actual target URL from DuckDuckGo redirect link.
    DDG search links typically look like: /l/?kh=-1&uddg=https%3A%2F%2Fwww.example.com%2F
    """
    if not href:
        return None
        
    if "uddg=" in href:
        try:
            parsed = urllib.parse.urlparse(href)
            query_params = urllib.parse.parse_qs(parsed.query)
            target_url = query_params.get("uddg", [None])[0]
            return target_url
        except Exception:
            pass
            
    if href.startswith("http://") or href.startswith("https://"):
        return href
        
    return None

def is_valid_company_website(url: str) -> bool:
    """Check if the URL is a valid company website and not a blacklist portal."""
    if not url:
        return False
        
    try:
        parsed = urllib.parse.urlparse(url)
        domain = (parsed.netloc or parsed.path).lower()
        if domain.startswith("www."):
            domain = domain[4:]
            
        # Check against blacklist
        if domain in DOMAINS_BLACKLIST:
            return False
            
        # Check if domain belongs to any blacklisted domain suffix (e.g. support.google.com)
        for blacklisted in DOMAINS_BLACKLIST:
            if domain == blacklisted or domain.endswith("." + blacklisted):
                return False
                
        return True
    except Exception:
        return False

async def discover_company_urls_ddg(keyword: str, max_pages: int = 2) -> Set[str]:
    """
    Query DuckDuckGo HTML search for a keyword and extract result URLs.
    Rotates user agents and crawls up to max_pages.
    """
    discovered_urls: Set[str] = set()
    logger.info(f"Starting DuckDuckGo discovery for keyword: '{keyword}' (max pages: {max_pages})")
    
    # We will fetch page by page
    for page_idx in range(max_pages):
        # Calculate search index offset if needed (s=0, s=30, s=50, etc.)
        offset = page_idx * 30
        
        # We can construct the search URL.
        # Format: https://html.duckduckgo.com/html/?q={query}&s={offset}
        encoded_query = urllib.parse.quote_plus(keyword)
        search_url = f"https://html.duckduckgo.com/html/?q={encoded_query}"
        if offset > 0:
            search_url += f"&s={offset}"
            
        logger.info(f"Fetching DDG search page: {search_url}")
        
        try:
            html_content, status = await browser_manager.fetch_page_content(search_url)
            if status != 200 or not html_content:
                logger.warning(f"Failed to fetch DDG page {page_idx} (status: {status})")
                break
                
            soup = BeautifulSoup(html_content, "html.parser")
            
            # Extract links from DDG HTML results
            # They are usually in tags: <a class="result__url" href="..."> or result__snippet
            result_links = soup.find_all("a", class_="result__url")
            
            if not result_links:
                # Let's try general links that contain DDG redirect patterns
                result_links = soup.find_all("a", href=True)
                
            page_found_count = 0
            for link in result_links:
                href = link.get("href", "")
                target_url = clean_url_from_ddg_redirect(href)
                
                if target_url and is_valid_company_website(target_url):
                    # Keep only base domain/home URL for direct crawler
                    parsed = urllib.parse.urlparse(target_url)
                    home_url = f"{parsed.scheme}://{parsed.netloc}/"
                    discovered_urls.add(home_url)
                    page_found_count += 1
            
            logger.info(f"Page {page_idx + 1}: Found {page_found_count} candidate URLs (Total so far: {len(discovered_urls)})")
            
            # Break if no links were found on this page
            if page_found_count == 0:
                break
                
            # Random delay between search pages
            await asyncio.sleep(random.uniform(1.0, 3.0))
            
        except Exception as e:
            logger.error(f"Error scraping search results on page {page_idx}: {e}")
            break
            
    return discovered_urls

async def run_discovery(keywords: List[str], max_pages: int = 2) -> Set[str]:
    """Run discovery concurrently or sequentially across multiple search keywords."""
    all_urls: Set[str] = set()
    
    # We run sequentially to avoid triggering IP blocks from DDG
    for kw in keywords:
        urls = await discover_company_urls_ddg(kw, max_pages=max_pages)
        all_urls.update(urls)
        # Sleep between keywords
        await asyncio.sleep(2.0)
        
    logger.info(f"Discovery complete. Discovered {len(all_urls)} unique company websites.")
    return all_urls
