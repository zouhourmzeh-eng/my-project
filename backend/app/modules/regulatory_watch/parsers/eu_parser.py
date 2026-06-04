from typing import List, Dict, Any
import feedparser
from datetime import datetime
from email.utils import parsedate_to_datetime
from bs4 import BeautifulSoup

from app.modules.regulatory_watch.parsers.base import BaseParser

class EuRegulatoryParser(BaseParser):
    """Parser for EU Regulatory updates (MDR, IVDR, MDCG)."""
    
    async def parse(self, url: str) -> List[Dict[str, Any]]:
        # EU feeds often use Atom or RSS
        feed = feedparser.parse(url)
        updates = []
        
        for entry in feed.entries:
            title = entry.get('title', '')
            link = entry.get('link', '')
            
            pub_date_str = entry.get('published', entry.get('updated', ''))
            pub_date = datetime.utcnow()
            if pub_date_str:
                try:
                    pub_date = parsedate_to_datetime(pub_date_str)
                    if pub_date.tzinfo:
                        pub_date = pub_date.replace(tzinfo=None)
                except Exception:
                    pass
            
            raw_summary = entry.get('description', entry.get('summary', ''))
            soup = BeautifulSoup(raw_summary, "html.parser")
            clean_summary = soup.get_text(separator=' ', strip=True)
            
            # Severity for EU docs
            severity = "medium"
            if any(word in title.lower() for word in ['corrigendum', 'amendment', 'urgent', 'infringement']):
                severity = "high"
            if "mdcg" in title.lower():
                severity = "medium" # Guidance is usually medium
            
            updates.append({
                "title": title,
                "publication_date": pub_date,
                "original_url": link,
                "summary": clean_summary,
                "severity": severity
            })
            
        return updates
