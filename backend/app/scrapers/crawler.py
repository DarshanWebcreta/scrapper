import asyncio
import logging
import urllib.parse
from bs4 import BeautifulSoup
from typing import Dict, Any, List, Set, Optional
from app.scrapers.base_scraper import browser_manager
from app.extractors.contact_extractor import (
    extract_contacts_from_html, 
    extract_clean_text, 
    extract_custom_fields_via_ai
)
from app.classifiers.classifier import classify_company
from app.utils.data_cleaner import extract_domain

logger = logging.getLogger("Crawler")

# Target subpage keywords to automatically crawl for contact and corporate details
SUBPAGE_KEYWORDS = [
    "contact", "about", "profile", "team", "export", 
    "management", "leadership", "careers", "investor"
]

def extract_subpage_links(soup: BeautifulSoup, base_url: str) -> List[str]:
    """Search the page for internal links matching contact/about/team/profile subpages."""
    base_parsed = urllib.parse.urlparse(base_url)
    base_domain = base_parsed.netloc.lower()
    
    candidate_urls: Set[str] = set()
    
    for a in soup.find_all('a', href=True):
        href = a['href'].strip()
        if not href or href.startswith('#') or href.startswith('javascript:'):
            continue
            
        absolute_url = urllib.parse.urljoin(base_url, href)
        parsed_absolute = urllib.parse.urlparse(absolute_url)
        
        # Ensure it belongs to the same domain
        if parsed_absolute.netloc.lower() != base_domain:
            continue
            
        path = parsed_absolute.path.lower()
        
        if any(keyword in path for keyword in SUBPAGE_KEYWORDS):
            clean_url = f"{parsed_absolute.scheme}://{parsed_absolute.netloc}{parsed_absolute.path}"
            if clean_url != base_url:
                candidate_urls.add(clean_url)
                
    return list(candidate_urls)

async def crawl_single_page(url: str) -> Optional[str]:
    """Fetch HTML content of a single page using browser manager."""
    try:
        content, status = await browser_manager.fetch_page_content(url)
        if status in [200, 201, 202] and content:
            return content
    except Exception as e:
        logger.debug(f"Error fetching page {url}: {e}")
    return None

async def crawl_company_website(
    website_url: str, 
    scrape_job_id: int, 
    fields_to_extract: List[str], 
    source: str = "Search"
) -> Optional[Dict[str, Any]]:
    """
    Crawls a single company website (homepage + contact/about subpages),
    extracts contact info, runs classification, extracts custom schema fields,
    and returns normalized entity and contacts dictionaries.
    """
    logger.info(f"Crawling website: {website_url}")
    
    # 1. Fetch homepage
    homepage_html = await crawl_single_page(website_url)
    if not homepage_html:
        logger.warning(f"Failed to crawl homepage: {website_url}")
        return None
        
    soup = BeautifulSoup(homepage_html, 'html.parser')
    
    # Extract contacts from homepage
    home_contacts = extract_contacts_from_html(homepage_html, website_url)
    
    # Extract subpage links
    subpage_links = extract_subpage_links(soup, website_url)
    
    # Limit to respectful crawl (max 3 subpages)
    subpages_to_crawl = subpage_links[:3]
    logger.info(f"Subpages found for {website_url}: {subpage_links}. Crawling: {subpages_to_crawl}")
    
    subpage_results: List[tuple] = []
    contact_page_used = website_url
    
    for sub_url in subpages_to_crawl:
        await asyncio.sleep(0.5)  # respectful crawl delay
        sub_html = await crawl_single_page(sub_url)
        if sub_html:
            subpage_results.append((sub_url, sub_html))
            if "contact" in sub_url.lower():
                contact_page_used = sub_url
                
    # 2. Merge contact data from all crawled pages
    merged_emails: Set[str] = set(home_contacts["emails"])
    merged_phones: Set[str] = set(home_contacts["phones"])
    merged_whatsapp: Set[str] = set(home_contacts["whatsapp"])
    
    address = home_contacts["address"]
    linkedin = home_contacts["linkedin"]
    facebook = home_contacts["facebook"]
    instagram = home_contacts["instagram"]
    twitter = home_contacts["twitter"]
    youtube = home_contacts["youtube"]
    company_name = home_contacts["company_name"]
    description = home_contacts["description"]
    
    # Accumulate page text for classification and AI extraction
    accumulated_text = extract_clean_text(homepage_html)
    
    for sub_url, sub_html in subpage_results:
        sub_contacts = extract_contacts_from_html(sub_html, sub_url)
        
        merged_emails.update(sub_contacts["emails"])
        merged_phones.update(sub_contacts["phones"])
        merged_whatsapp.update(sub_contacts["whatsapp"])
        
        if sub_contacts["address"] and not address:
            address = sub_contacts["address"]
        if sub_contacts["linkedin"] and not linkedin:
            linkedin = sub_contacts["linkedin"]
        if sub_contacts["facebook"] and not facebook:
            facebook = sub_contacts["facebook"]
        if sub_contacts["instagram"] and not instagram:
            instagram = sub_contacts["instagram"]
        if sub_contacts["twitter"] and not twitter:
            twitter = sub_contacts["twitter"]
        if sub_contacts["youtube"] and not youtube:
            youtube = sub_contacts["youtube"]
            
        accumulated_text += " " + extract_clean_text(sub_html)
        
    accumulated_text = " ".join(accumulated_text.split())
    
    # 3. AI Classify Company
    classification_res = await classify_company(accumulated_text, website_url)
    
    # 4. Extract Dynamic Custom Fields (Ollama / AI fallback)
    # Filter fields requested by user that are NOT part of the standard fields
    standard_fields = [
        "company_name", "website", "emails", "phones", "whatsapp", 
        "linkedin", "facebook", "instagram", "twitter", "youtube", 
        "address", "country", "classification", "industry", "description"
    ]
    custom_fields = [f for f in fields_to_extract if f not in standard_fields]
    
    extracted_custom_data = {}
    if custom_fields:
        logger.info(f"Extracting custom fields {custom_fields} via Ollama fallback...")
        extracted_custom_data = await extract_custom_fields_via_ai(
            accumulated_text, 
            custom_fields, 
            website_url
        )
        
    # Compile entity structure
    entity_data = {
        "scrape_job_id": scrape_job_id,
        "company_name": company_name,
        "website": website_url,
        "domain": extract_domain(website_url),
        "description": description or classification_res.get("description"),
        "country": classification_res.get("country", "Unknown"),
        "address": address,
        "classification": classification_res.get("classification", "unknown"),
        "industry": classification_res.get("industry", "Other"),
        "source": source,
        "contact_page": contact_page_used,
        "status": "crawled",
        "extracted_data": extracted_custom_data
    }
    
    # Compile contacts structured list
    contacts_list = []
    for email in merged_emails:
        contacts_list.append({"type": "email", "value": email})
    for phone in merged_phones:
        contacts_list.append({"type": "phone", "value": phone})
    for whatsapp in merged_whatsapp:
        contacts_list.append({"type": "whatsapp", "value": whatsapp})
    if linkedin:
        contacts_list.append({"type": "linkedin", "value": linkedin})
    if facebook:
        contacts_list.append({"type": "facebook", "value": facebook})
    if instagram:
        contacts_list.append({"type": "instagram", "value": instagram})
    if twitter:
        contacts_list.append({"type": "twitter", "value": twitter})
    if youtube:
        contacts_list.append({"type": "youtube", "value": youtube})
        
    return {
        "entity": entity_data,
        "contacts": contacts_list
    }
