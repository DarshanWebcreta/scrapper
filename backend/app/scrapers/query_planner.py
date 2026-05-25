import logging
import httpx
import json
import re
from typing import List, Optional
from app.config import settings

logger = logging.getLogger("QueryPlanner")

SYNONYMS = {
    "manufacturer": ["factory", "producer", "exporter", "supplier", "manufacturing plant"],
    "manufacturers": ["factories", "producers", "exporters", "suppliers", "companies"],
    "hospital": ["medical center", "clinic", "healthcare provider", "infirmary"],
    "hospitals": ["medical centers", "clinics", "healthcare providers", "healthcare facilities"],
    "startup": ["tech company", "software company", "fintech startup", "new venture"],
    "startups": ["tech companies", "software companies", "fintech startups", "innovators"],
    "restaurant": ["cafe", "diner", "bistro", "eatery", "food joint"],
    "restaurants": ["cafes", "diners", "bistros", "eateries", "food joints"],
    "supplier": ["distributor", "wholesaler", "trader", "reseller", "vendor"],
    "suppliers": ["distributors", "wholesalers", "traders", "resellers", "vendors"],
}

def clean_query_input(user_query: str) -> str:
    """Strip common search command prefixes."""
    cleaned = re.sub(r'^(find|search for|get|retrieve|discover|look up|show me)\s+', '', user_query, flags=re.IGNORECASE)
    return cleaned.strip()

def run_rule_based_query_planner(user_query: str, countries: Optional[List[str]] = None) -> List[str]:
    """
    Fallback query planner using synonyms and template replacement.
    Generates 3 to 5 distinct search phrases.
    """
    cleaned = clean_query_input(user_query)
    country_suffix = f" in {countries[0]}" if countries and len(countries) > 0 else ""
    
    variations = [f"{cleaned}{country_suffix}"]
    
    # Try replacing words with synonyms
    words = cleaned.split()
    for i, word in enumerate(words):
        word_lower = word.lower()
        if word_lower in SYNONYMS:
            for syn in SYNONYMS[word_lower][:4]:
                new_words = list(words)
                new_words[i] = syn
                new_query = " ".join(new_words)
                variations.append(f"{new_query}{country_suffix}")
                if len(variations) >= 5:
                    break
        if len(variations) >= 5:
            break
            
    # Add a generic fallback template if variations are short
    if len(variations) < 3 and country_suffix:
        variations.append(f"companies{country_suffix} {cleaned}")
        variations.append(f"best {cleaned}{country_suffix}")
        
    return list(set(variations))[:5]

async def plan_search_queries(user_query: str, countries: Optional[List[str]] = None) -> List[str]:
    """
    Generates dynamic search query variations for the scraping engine.
    Tries Ollama if configured and active, falls back to rule-based template.
    """
    cleaned = clean_query_input(user_query)
    country_str = ", ".join(countries) if countries else "Global"
    
    ollama_url = f"{settings.OLLAMA_HOST}/api/generate"
    prompt = (
        "You are an expert search strategist. Given the business search query and the target countries below, "
        "generate exactly 5 high-converting search variations that can be used on DuckDuckGo or Google to find direct company websites.\n\n"
        f"Query Topic: \"{cleaned}\"\n"
        f"Target Location: \"{country_str}\"\n\n"
        "Return ONLY a raw JSON list of strings (e.g. [\"variation 1\", \"variation 2\", ...]). Do not include markdown code block formatting (like ```json), just raw text."
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
                        "temperature": 0.2
                    }
                }
            )
            if response.status_code == 200:
                res_data = response.json()
                response_text = res_data.get("response", "").strip()
                if response_text.startswith("```"):
                    response_text = response_text.strip("`").replace("json", "", 1).strip()
                
                parsed = json.loads(response_text)
                if isinstance(parsed, list) and len(parsed) > 0:
                    logger.info(f"Ollama successfully generated search variations: {parsed}")
                    return parsed
    except Exception as e:
        logger.debug(f"Ollama query planner failed or timed out: {e}. Falling back to rule-based.")
        
    fallback = run_rule_based_query_planner(user_query, countries)
    logger.info(f"Rule-based query planner generated: {fallback}")
    return fallback
