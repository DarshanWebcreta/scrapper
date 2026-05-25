import re
import logging
import httpx
import json
from urllib.parse import urlparse
from bs4 import BeautifulSoup
from typing import Dict, Any, List, Set
from app.config import settings
from app.utils.data_cleaner import clean_email, clean_phone, extract_domain

logger = logging.getLogger("ExtractionEngine")

# Regex patterns for contact discovery
EMAIL_REGEX = re.compile(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}')
PHONE_REGEX = re.compile(r'(?:\+?\d{1,4}[-.\s]?)?(?:\(?\d{2,5}\)?[-.\s]?)?\d{3,5}[-.\s]?\d{3,6}')

# Social media profile links patterns
LINKEDIN_REGEX = re.compile(r'https?://(?:www\.)?linkedin\.com/(?:in|company)/[a-zA-Z0-9-_]+')
FACEBOOK_REGEX = re.compile(r'https?://(?:www\.)?facebook\.com/[a-zA-Z0-9._-]+')
INSTAGRAM_REGEX = re.compile(r'https?://(?:www\.)?instagram\.com/[a-zA-Z0-9._-]+')
TWITTER_REGEX = re.compile(r'https?://(?:www\.)?(?:twitter\.com|x\.com)/[a-zA-Z0-9._-]+')
YOUTUBE_REGEX = re.compile(r'https?://(?:www\.)?youtube\.com/(?:c|channel|user|@)?[a-zA-Z0-9-_]+')

# WhatsApp links pattern
WHATSAPP_REGEX = re.compile(r'(?:https?://(?:wa\.me|api\.whatsapp\.com/send\?phone=)|whatsapp:/?/?)([0-9+]+)')

def extract_schema_data(html_content: str, url: str) -> Dict[str, Any]:
    """Parse schema.org JSON-LD and microdata from HTML page using extruct."""
    extracted = {}
    try:
        import extruct
        data = extruct.extract(html_content, base_url=url, syntaxes=['json-ld', 'microdata', 'opengraph'])
        
        # 1. Parse JSON-LD
        for item in data.get('json-ld', []):
            if not isinstance(item, dict):
                continue
            type_ = item.get('@type')
            if type_ in ['Organization', 'LocalBusiness', 'Corporation', 'Store', 'Hospital']:
                if 'name' in item and not extracted.get('company_name'):
                    extracted['company_name'] = item['name']
                if 'email' in item:
                    extracted['email'] = item['email']
                if 'telephone' in item:
                    extracted['telephone'] = item['telephone']
                if 'description' in item:
                    extracted['description'] = item['description']
                if 'address' in item:
                    addr = item['address']
                    if isinstance(addr, dict):
                        parts = [addr.get('streetAddress'), addr.get('addressLocality'), addr.get('addressRegion'), addr.get('postalCode'), addr.get('addressCountry')]
                        extracted['address'] = ", ".join([str(p) for p in parts if p])
                    elif isinstance(addr, str):
                        extracted['address'] = addr

        # 2. Parse OpenGraph fallback
        og = data.get('opengraph', [])
        if og and isinstance(og, list):
            first_og = og[0]
            if isinstance(first_og, dict):
                if 'og:site_name' in first_og and not extracted.get('company_name'):
                    extracted['company_name'] = first_og['og:site_name']
                if 'og:description' in first_og and not extracted.get('description'):
                    extracted['description'] = first_og['og:description']
    except Exception as e:
        logger.debug(f"Extruct failed: {e}")
    return extracted

def extract_clean_text(html_content: str) -> str:
    """Extract main text from HTML body using trafilatura, falling back to BeautifulSoup."""
    try:
        import trafilatura
        text = trafilatura.extract(html_content)
        if text:
            return text
    except Exception:
        pass
    
    # Fallback
    try:
        soup = BeautifulSoup(html_content, 'html.parser')
        # Remove script and style elements
        for script in soup(["script", "style"]):
            script.decompose()
        return soup.get_text(separator=' ')
    except Exception:
        return ""

async def extract_custom_fields_via_ai(text: str, fields: List[str], url: str) -> Dict[str, Any]:
    """Uses Gemini API (if key provided) or local Ollama model to dynamically extract user requested custom fields from page text."""
    if not fields:
        return {}
        
    # Clean text to fit context prompt window
    snippet = text[:3500].replace('\n', ' ').strip()
    if not snippet:
        return {}
        
    fields_desc = ", ".join([f'"{f}"' for f in fields])
    prompt = (
        "You are a structured data extractor.\n"
        f"URL: {url}\n"
        f"Web content snippet: {snippet}\n\n"
        f"Extract values for the following keys: {fields_desc}.\n"
        "Return ONLY a valid JSON object. If a value is not found, set it to null. Ensure exact key matches."
    )
    
    # 1. Try Gemini API if key is provided
    if settings.GEMINI_API_KEY:
        try:
            gemini_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={settings.GEMINI_API_KEY}"
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    gemini_url,
                    json={
                        "contents": [{"parts": [{"text": prompt}]}],
                        "generationConfig": {
                            "responseMimeType": "application/json"
                        }
                    }
                )
                if response.status_code == 200:
                    res_data = response.json()
                    response_text = res_data["candidates"][0]["content"]["parts"][0]["text"].strip()
                    parsed = json.loads(response_text)
                    if isinstance(parsed, dict):
                        return parsed
        except Exception as e:
            logger.debug(f"Gemini custom field extraction failed/timed out: {e}. Trying Ollama...")

    # 2. Try Ollama (Local AI)
    ollama_url = f"{settings.OLLAMA_HOST}/api/generate"
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            response = await client.post(
                ollama_url,
                json={
                    "model": settings.OLLAMA_MODEL,
                    "prompt": prompt + " Do not include markdown code block formats (like ```json), just raw JSON.",
                    "stream": False,
                    "options": {
                        "temperature": 0.0
                    }
                }
            )
            if response.status_code == 200:
                res_data = response.json()
                response_text = res_data.get("response", "").strip()
                if response_text.startswith("```"):
                    response_text = response_text.strip("`").replace("json", "", 1).strip()
                
                parsed = json.loads(response_text)
                if isinstance(parsed, dict):
                    return parsed
    except Exception as e:
        logger.debug(f"Ollama custom field extraction failed/timed out: {e}")
    return {}

def extract_contacts_from_html(html_content: str, url: str) -> Dict[str, Any]:
    """Extract standard contacts (emails, phones, socials, whatsapp) and basic metadata from page HTML."""
    soup = BeautifulSoup(html_content, 'html.parser')
    text_content = soup.get_text(separator=' ')
    
    emails: Set[str] = set()
    phones: Set[str] = set()
    whatsapp_numbers: Set[str] = set()
    
    # 1. Parse anchors for mailto/tel/whatsapp
    for a in soup.find_all('a', href=True):
        href = a['href'].strip()
        if href.startswith('mailto:'):
            email = href.replace('mailto:', '').split('?')[0].strip()
            cleaned = clean_email(email)
            if cleaned:
                emails.add(cleaned)
        elif href.startswith('tel:'):
            phone = href.replace('tel:', '').split('?')[0].strip()
            cleaned = clean_phone(phone)
            if cleaned:
                phones.add(cleaned)
        elif 'wa.me' in href or 'api.whatsapp.com' in href:
            match = WHATSAPP_REGEX.search(href)
            if match:
                whatsapp_numbers.add(match.group(1).strip('+'))
                
    # 2. General regex search on page text
    for email in EMAIL_REGEX.findall(text_content):
        cleaned = clean_email(email)
        if cleaned:
            emails.add(cleaned)
            
    for phone in PHONE_REGEX.findall(text_content):
        cleaned = clean_phone(phone)
        if cleaned and len(cleaned) >= 8:
            phones.add(cleaned)

    # 3. Social media profile link extraction
    linkedin = None
    facebook = None
    instagram = None
    twitter = None
    youtube = None
    
    for a in soup.find_all('a', href=True):
        href = a['href'].strip()
        if not linkedin:
            match = LINKEDIN_REGEX.search(href)
            if match:
                linkedin = match.group(0)
        if not facebook:
            match = FACEBOOK_REGEX.search(href)
            if match:
                facebook = match.group(0)
        if not instagram:
            match = INSTAGRAM_REGEX.search(href)
            if match:
                instagram = match.group(0)
        if not twitter:
            match = TWITTER_REGEX.search(href)
            if match:
                twitter = match.group(0)
        if not youtube:
            match = YOUTUBE_REGEX.search(href)
            if match:
                youtube = match.group(0)

    # 4. Extract schema organization details
    schema_details = extract_schema_data(html_content, url)
    
    # Guess company name from title
    company_name = schema_details.get("company_name")
    if not company_name:
        title = soup.find('title')
        if title and title.text:
            text = title.text.strip()
            for splitter in ['|', '-', '—', ':', '•']:
                if splitter in text:
                    parts = text.split(splitter)
                    filtered = [p.strip() for p in parts if p.strip().lower() not in ['home', 'about', 'contact', 'about us', 'contact us', 'welcome']]
                    if filtered:
                        company_name = filtered[0]
                        break
            if not company_name:
                company_name = text
        if not company_name:
            domain = extract_domain(url)
            if domain:
                company_name = domain.split('.')[0].capitalize()
            else:
                company_name = "Unknown Company"

    # Capture address
    address = schema_details.get("address")
    if not address:
        addr_tag = soup.find('address')
        if addr_tag:
            address = re.sub(r'\s+', ' ', addr_tag.get_text().strip())
        else:
            for tag in ['div', 'span', 'p', 'footer']:
                elements = soup.find_all(tag, class_=lambda c: c and any(w in str(c).lower() for w in ['address', 'footer-addr', 'company-address']))
                for el in elements:
                    text = re.sub(r'\s+', ' ', el.get_text().strip())
                    if 15 < len(text) < 200 and any(c.isdigit() for c in text) and not re.match(r'^\+?[0-9()\s-]+$', text):
                        address = text
                        break
                if address:
                    break

    return {
        "company_name": company_name,
        "description": schema_details.get("description"),
        "emails": list(emails),
        "phones": list(phones),
        "whatsapp": list(whatsapp_numbers),
        "linkedin": linkedin,
        "facebook": facebook,
        "instagram": instagram,
        "twitter": twitter,
        "youtube": youtube,
        "address": address
    }
