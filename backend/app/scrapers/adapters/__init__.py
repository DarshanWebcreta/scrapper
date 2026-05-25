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

def select_adapters(query: str) -> List[BaseAdapter]:
    """
    Dynamically select directories and search adapters based on keywords in the query.
    Always includes Google and DuckDuckGo as general fallback search engines.
    """
    query_lower = query.lower()
    selected: List[BaseAdapter] = []
    
    # 1. B2B / Manufacturing / Industrial directories
    b2b_keywords = [
        "manufacturer", "factory", "producer", "supplier", "packaging", 
        "brewery", "footwear", "bottle", "exporter", "importer", "chemical",
        "industrial", "wholesale", "distributor"
    ]
    if any(k in query_lower for k in b2b_keywords):
        selected.append(_europages_adapter)
        selected.append(_thomasnet_adapter)
        selected.append(_indiamart_adapter)
        logger.info("Selected B2B directories: Europages, ThomasNet, IndiaMART")
        
    # 2. Local business directories (restaurants, hospitals, clinics, retail shops)
    local_keywords = [
        "restaurant", "cafe", "hotel", "bakery", "hospital", "clinic", 
        "medical", "doctor", "dentist", "pharmacy", "store", "shop", 
        "salon", "school", "logistics", "courier"
    ]
    if any(k in query_lower for k in local_keywords):
        selected.append(_yellowpages_adapter)
        logger.info("Selected Local directories: YellowPages")
        
    # 3. Always include general web search (Google and DuckDuckGo)
    selected.append(_google_adapter)
    selected.append(_ddg_adapter)
    
    return selected
