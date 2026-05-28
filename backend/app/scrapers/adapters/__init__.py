import logging
from typing import List
from app.scrapers.adapters.base_adapter import BaseAdapter
from app.scrapers.adapters.google import GoogleAdapter
from app.scrapers.adapters.duckduckgo import DuckDuckGoAdapter
from app.scrapers.adapters.europages import EuropagesAdapter
from app.scrapers.adapters.thomasnet import ThomasNetAdapter
from app.scrapers.adapters.indiamart import IndiaMartAdapter
from app.scrapers.adapters.yellowpages import YellowPagesAdapter

logger = logging.getLogger("AdaptersRegistry")

# Initialize singleton instances of adapters
_google_adapter = GoogleAdapter()
_ddg_adapter = DuckDuckGoAdapter()
_europages_adapter = EuropagesAdapter()
_thomasnet_adapter = ThomasNetAdapter()
_indiamart_adapter = IndiaMartAdapter()
_yellowpages_adapter = YellowPagesAdapter()

def select_adapters(query: str, countries: List[str] = None) -> List[BaseAdapter]:
    """
    Dynamically select directories and search adapters based on keywords in the query
    and target countries. Always includes Google and DuckDuckGo as fallback.
    """
    query_lower = query.lower()
    selected: List[BaseAdapter] = []
    
    # Normalize country list to lowercase
    countries_lower = [c.lower() for c in countries] if countries else []
    
    # European countries list (partial common list)
    europe_countries = {
        "germany", "france", "italy", "spain", "united kingdom", "uk", "netherlands", 
        "poland", "belgium", "switzerland", "austria", "sweden", "norway", "denmark",
        "finland", "ireland", "portugal", "greece", "turkey", "europe"
    }
    
    # North American countries
    na_countries = {"usa", "united states", "america", "canada", "mexico"}
    
    # India
    india_countries = {"india", "ind"}
    
    # 1. B2B / Manufacturing / Industrial directories
    b2b_keywords = [
        "manufacturer", "factory", "producer", "supplier", "packaging", 
        "brewery", "footwear", "bottle", "exporter", "importer", "chemical",
        "industrial", "wholesale", "distributor"
    ]
    if any(k in query_lower for k in b2b_keywords):
        # Determine which directories match the target countries
        is_global = not countries_lower
        
        has_europe = is_global or any(c in europe_countries for c in countries_lower)
        has_na = is_global or any(c in na_countries for c in countries_lower)
        has_india = is_global or any(c in india_countries for c in countries_lower)
        
        if has_europe:
            selected.append(_europages_adapter)
        if has_na:
            selected.append(_thomasnet_adapter)
        if has_india:
            selected.append(_indiamart_adapter)
            
        logger.info(f"Selected B2B directories: {[a.name for a in selected]}")
        
    # 2. Local business directories (restaurants, hospitals, clinics, retail shops)
    local_keywords = [
        "restaurant", "cafe", "hotel", "bakery", "hospital", "clinic", 
        "medical", "doctor", "dentist", "pharmacy", "store", "shop", 
        "salon", "school", "logistics", "courier"
    ]
    if any(k in query_lower for k in local_keywords):
        # YellowPages is primarily US-focused
        is_global = not countries_lower
        has_na = is_global or any(c in na_countries for c in countries_lower)
        if has_na:
            selected.append(_yellowpages_adapter)
            logger.info("Selected Local directories: YellowPages")
        
    # 3. Always include general web search (Google and DuckDuckGo)
    selected.append(_google_adapter)
    selected.append(_ddg_adapter)
    
    return selected
