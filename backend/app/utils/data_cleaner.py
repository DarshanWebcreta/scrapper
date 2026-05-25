import re
from urllib.parse import urlparse
from typing import Set, List

# Standard email regex pattern
EMAIL_REGEX = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')

# Media/Static files extensions to exclude from email endings
EMAIL_BLACKLIST_EXTENSIONS = {
    'png', 'jpg', 'jpeg', 'gif', 'svg', 'webp', 'css', 'js', 'pdf', 'mp3',
    'mp4', 'zip', 'gz', 'tar', 'xml', 'json', 'wixpress', 'sentry', 'wix', 'png@2x'
}

# Country normalization map
COUNTRY_MAP = {
    "us": "United States",
    "usa": "United States",
    "united states of america": "United States",
    "uk": "United Kingdom",
    "gb": "United Kingdom",
    "great britain": "United Kingdom",
    "de": "Germany",
    "deutschland": "Germany",
    "tr": "Turkey",
    "turkiye": "Turkey",
    "in": "India",
    "cn": "China",
    "uae": "United Arab Emirates",
    "united arab emirates": "United Arab Emirates",
    "sg": "Singapore",
    "mx": "Mexico",
    "br": "Brazil",
    "fr": "France",
    "it": "Italy"
}

def clean_phone(phone: str) -> str:
    """Normalize phone numbers, stripping unwanted characters but keeping '+'."""
    if not phone:
        return ""
    # Remove everything except digits and '+'
    cleaned = re.sub(r'[^\d+]', '', phone).strip()
    # Check if number of digits is within standard range (7 to 15 digits)
    digit_count = sum(c.isdigit() for c in cleaned)
    if 7 <= digit_count <= 18:
        return cleaned
    return ""

def clean_email(email: str) -> str:
    """Validate email formatting and check against static file endings."""
    if not email:
        return ""
    email = email.strip().lower()
    if not EMAIL_REGEX.match(email):
        return ""
    parts = email.split('.')
    if parts and parts[-1] in EMAIL_BLACKLIST_EXTENSIONS:
        return ""
    return email

def extract_domain(url: str) -> str:
    """Extract a clean base domain from a full URL."""
    if not url:
        return ""
    try:
        parsed = urlparse(url)
        domain = parsed.netloc or parsed.path
        if domain.startswith("www."):
            domain = domain[4:]
        # Strip port if present
        domain = domain.split(":")[0]
        return domain.lower().strip()
    except Exception:
        return ""

def normalize_country(country: str) -> str:
    """Map country codes and variations to clean capitalized country names."""
    if not country:
        return "Unknown"
    clean_name = country.strip().lower()
    if clean_name in COUNTRY_MAP:
        return COUNTRY_MAP[clean_name]
    return country.strip().title()

def clean_url(url: str) -> str:
    """Ensure URL is properly formatted with a protocol."""
    if not url:
        return ""
    url = url.strip()
    if not url.startswith("http://") and not url.startswith("https://"):
        url = "https://" + url
    return url
