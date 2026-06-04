from abc import ABC, abstractmethod
from typing import List, Dict, Any

class BaseParser(ABC):
    """Base class for regulatory source parsers."""
    
    @abstractmethod
    async def parse(self, url: str) -> List[Dict[str, Any]]:
        """
        Parses a regulatory source and returns a list of standardized update dictionaries.
        Expected dictionary keys:
        - title (str)
        - publication_date (datetime)
        - original_url (str)
        - summary (str) - Optional, raw summary before AI processing
        - severity (str) - Optional hint for severity
        """
        pass
