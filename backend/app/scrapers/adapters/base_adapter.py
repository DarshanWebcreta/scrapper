from typing import Set, Optional

class BaseAdapter:
    def __init__(self, name: str):
        self.name = name

    async def search(self, keyword: str, country: Optional[str] = None, max_pages: int = 1) -> Set[str]:
        """
        Query the source and return a set of website homepage URLs.
        Each URL should be cleaned (e.g. protocol and domain only).
        """
        raise NotImplementedError
