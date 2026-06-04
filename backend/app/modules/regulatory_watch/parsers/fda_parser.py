from typing import List, Dict, Any
import feedparser
from datetime import datetime
from email.utils import parsedate_to_datetime
from bs4 import BeautifulSoup

from app.modules.regulatory_watch.parsers.base import BaseParser

class FdaRssParser(BaseParser):
    """Parser for FDA RSS feeds."""
    
    async def parse(self, url: str) -> List[Dict[str, Any]]:
        # feedparser blocks on network by default, but it's acceptable for background worker
        # Alternatively, we could fetch with httpx and pass string to feedparser
        feed = feedparser.parse(url)
        print(f"DEBUG: Found {len(feed.entries)} entries for {url}")
        updates = []
        
        for entry in feed.entries:
            title = entry.get('title', '')
            link = entry.get('link', '')
            
            # Parse publication date
            pub_date_str = entry.get('published', entry.get('updated', ''))
            pub_date = datetime.utcnow()
            if pub_date_str:
                try:
                    pub_date = parsedate_to_datetime(pub_date_str)
                    # Convert to naive utc if timezone aware
                    if pub_date.tzinfo:
                        pub_date = pub_date.replace(tzinfo=None)
                except Exception:
                    pass
            
            # Parse description/summary, clean HTML
            raw_summary = entry.get('description', entry.get('summary', ''))
            soup = BeautifulSoup(raw_summary, "html.parser")
            clean_summary = soup.get_text(separator=' ', strip=True)
            
            # Try to guess severity from title/summary
            severity = "medium"
            if any(word in title.lower() for word in ['recall', 'urgent', 'warning', 'critical', 'cybersecurity']):
                severity = "high"
            
            updates.append({
                "title": title,
                "publication_date": pub_date,
                "original_url": link,
                "summary": clean_summary,
                "severity": severity
            })
            
        return updates
