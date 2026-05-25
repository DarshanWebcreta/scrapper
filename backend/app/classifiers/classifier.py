import httpx
import json
import logging
import re
from typing import Dict, Any, List
from urllib.parse import urlparse
from app.config import settings
from app.utils.data_cleaner import normalize_country

logger = logging.getLogger("Classifier")

# Expanded country TLD mappings
TLD_COUNTRY_MAP = {
    ".cn": "China",
    ".in": "India",
    ".de": "Germany",
    ".it": "Italy",
    ".fr": "France",
    ".uk": "United Kingdom",
    ".co.uk": "United Kingdom",
    ".es": "Spain",
    ".jp": "Japan",
    ".br": "Brazil",
    ".ru": "Russia",
    ".ca": "Canada",
    ".au": "Australia",
    ".nl": "Netherlands",
    ".pl": "Poland",
    ".tr": "Turkey",
    ".vn": "Vietnam",
    ".tw": "Taiwan",
    ".kr": "South Korea",
    ".my": "Malaysia",
    ".th": "Thailand",
    ".pk": "Pakistan",
    ".mx": "Mexico",
    ".eg": "Egypt",
    ".za": "South Africa",
    ".ae": "United Arab Emirates",
    ".sg": "Singapore"
}

# Rule-based classification keyword lists
CLASSIFICATION_KEYWORDS = {
    "manufacturer": [
        "manufacturer", "factory", "producer", "production line", "manufacturing facility", 
        "manufacturing plant", "blowing machine", "molding machine", "injection molding", 
        "oem", "odm", "fabrication", "our factory", "production capacity", "facilities"
    ],
    "distributor": [
        "distributor", "distribution", "wholesale", "wholesaler", "stockist", 
        "reseller", "dealer", "supply chain", "supplying", "logistics"
    ],
    "trader": [
        "trader", "trading", "import-export", "import export", "trading company", 
        "exporter", "importer", "agent", "sourcing agent", "broker"
    ],
    "hospital": [
        "hospital", "clinic", "medical center", "healthcare", "patient", "physician",
        "doctor", "dentist", "treatment", "medicine", "surgical", "emergency care"
    ],
    "restaurant": [
        "restaurant", "cafe", "bistro", "eatery", "food", "beverage", "menu", "dining",
        "kitchen", "chef", "order online", "dine-in", "takeout", "bar"
    ],
    "tech company": [
        "software", "saas", "developer", "technology", "cloud", "platform", "app",
        "api", "database", "it solutions", "systems integrator", "cybersecurity"
    ],
    "startup": [
        "startup", "fintech", "biotech", "venture", "funding", "seed round", 
        "series a", "incubator", "accelerator", "co-founder"
    ],
    "logistics company": [
        "logistics", "shipping", "freight", "transportation", "warehouse", 
        "cargo", "courier", "delivery", "supply chain solutions", "trucking"
    ]
}

# Industry keywords mapping
INDUSTRY_KEYWORDS = {
    "Manufacturing": ["manufacturer", "factory", "packaging", "blowing", "extrusion"],
    "Healthcare": ["hospital", "clinic", "medical", "doctor", "dentist", "patient"],
    "Technology": ["software", "saas", "tech", "cloud", "artificial intelligence", "app"],
    "Food & Beverage": ["restaurant", "cafe", "food", "beverage", "brewery", "wine", "beer"],
    "Logistics": ["shipping", "logistics", "transport", "cargo", "warehouse", "freight"],
    "Finance": ["fintech", "banking", "finance", "investment", "funding"]
}

def rule_based_country_detect(url: str, text: str) -> str:
    """Guess country using URL TLD and keyword search."""
    parsed = urlparse(url)
    domain = (parsed.netloc or parsed.path).lower()
    
    # Check TLD ending
    for tld, country in TLD_COUNTRY_MAP.items():
        if domain.endswith(tld):
            return country
            
    # Search common country names in text
    text_lower = text.lower()
    for tld, country in TLD_COUNTRY_MAP.items():
        if re.search(r'\b' + re.escape(country.lower()) + r'\b', text_lower):
            return country
            
    if "usa" in text_lower or "united states" in text_lower:
        return "United States"
    if "china" in text_lower:
        return "China"
    if "india" in text_lower:
        return "India"
    if "germany" in text_lower:
        return "Germany"
    if "turkey" in text_lower or "turkiye" in text_lower:
        return "Turkey"
    if "uae" in text_lower or "united arab emirates" in text_lower:
        return "United Arab Emirates"
    if "singapore" in text_lower:
        return "Singapore"
        
    return "Unknown"

def run_rule_based_classification(text: str, url: str) -> Dict[str, Any]:
    """Fallback classifier that uses regex and word lists to categorize the business and industry."""
    text_lower = text.lower()
    
    # 1. Determine classification type
    detected_class = "unknown"
    max_matches = 0
    
    for category, keywords in CLASSIFICATION_KEYWORDS.items():
        matches = sum(1 for kw in keywords if kw in text_lower)
        if matches > max_matches:
            max_matches = matches
            detected_class = category
            
    # 2. Determine industry
    detected_industry = "Other"
    max_ind_matches = 0
    for industry, keywords in INDUSTRY_KEYWORDS.items():
        matches = sum(1 for kw in keywords if kw in text_lower)
        if matches > max_ind_matches:
            max_ind_matches = matches
            detected_industry = industry
            
    # 3. Determine country
    detected_country = rule_based_country_detect(url, text)
    
    return {
        "classification": detected_class,
        "industry": detected_industry,
        "country": normalize_country(detected_country),
        "method": "rules"
    }

async def classify_company(text: str, url: str) -> Dict[str, Any]:
    """
    Classifies a company based on webpage text.
    First tries Ollama (local AI). If unavailable/error, falls back to rule-based.
    """
    snippet = text[:2500].replace('\n', ' ').strip()
    if not snippet:
        return run_rule_based_classification("", url)
        
    ollama_url = f"{settings.OLLAMA_HOST}/api/generate"
    prompt = (
        "You are an AI assistant classifying companies from web content.\n"
        f"URL: {url}\n"
        f"Web content snippet: {snippet}\n\n"
        "Please classify this company and reply ONLY with a JSON object. Do not include markdown code block syntax (like ```json), just raw JSON. The JSON keys must be:\n"
        "1. \"classification\": string (must be one of: \"manufacturer\", \"supplier\", \"trader\", \"distributor\", \"reseller\", \"hospital\", \"restaurant\", \"tech company\", \"startup\", \"logistics company\", \"unknown\")\n"
        "2. \"industry\": string (e.g. \"Packaging\", \"Cosmetics\", \"Beverages\", \"Pharma\", \"Healthcare\", \"Food & Beverage\", \"Logistics\", \"Technology\", \"Retail\")\n"
        "3. \"country\": string (the country where the company is based, e.g. \"China\", \"United States\", \"Germany\", \"India\", \"Turkey\", \"Singapore\", \"Unknown\")\n"
        "4. \"description\": string (brief 1-sentence summary of what they do)"
    )
    
    try:
        async with httpx.AsyncClient(timeout=4.0) as client:
            response = await client.post(
                ollama_url,
                json={
                    "model": settings.OLLAMA_MODEL,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.1
                    }
                }
            )
            if response.status_code == 200:
                res_data = response.json()
                response_text = res_data.get("response", "").strip()
                if response_text.startswith("```"):
                    response_text = response_text.strip("`").replace("json", "", 1).strip()
                
                parsed = json.loads(response_text)
                if "country" in parsed:
                    parsed["country"] = normalize_country(parsed["country"])
                parsed["method"] = f"ollama ({settings.OLLAMA_MODEL})"
                logger.info(f"Ollama classification successful for {url}: {parsed.get('classification')}")
                return parsed
    except Exception as e:
        logger.debug(f"Ollama classification failed: {e}. Falling back to rule-based.")
        
    return run_rule_based_classification(text, url)
