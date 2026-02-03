"""USC Cinema scraper"""
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import pytz
from typing import List, Dict, Optional
import re

from scrapers.parsers.movie_normalizer import normalize_title


class USCCinemaScraper:
    """Scraper for USC School of Cinematic Arts screenings"""
    
    URL = "https://cinema.usc.edu/events/index.cfm"
    BASE_URL = "https://cinema.usc.edu"
    
    def __init__(self):
        self.pacific_tz = pytz.timezone('America/Los_Angeles')
    
    def scrape_schedule(self) -> List[Dict]:
        """Scrape upcoming screenings"""
        print(f"   Fetching: {self.URL}")
        
        try:
            response = requests.get(self.URL, timeout=10)
            response.raise_for_status()
        except requests.RequestException as e:
            print(f"   ❌ Error fetching: {e}")
            return []
        
        soup = BeautifulSoup(response.text, 'html.parser')
        screenings = []
        
        # Find all event items
        event_items = soup.find_all('div', class_='newsItem')
        print(f"   Found {len(event_items)} events")
        
        for item in event_items:
            screening = self._parse_event(item)
            if screening:
                screenings.append(screening)
        
        return screenings
    
    def _parse_event(self, item) -> Optional[Dict]:
        """Parse a single event item"""
        try:
            # Get title and link
            title_elem = item.select_one('h5 a')
            if not title_elem:
                return None
            
            raw_title = title_elem.get_text().strip()
            event_url = title_elem.get('href', '')
            if event_url and not event_url.startswith('http'):
                event_url = self.BASE_URL + event_url
            
            # Filter out non-cinema events
            # Skip administrative events, info sessions, etc.
            skip_keywords = [
                'information session', 'admissions', 'open house',
                'workshop', 'seminar', 'lecture', 'panel',
                'trojan family', 'graduation', 'commencement',
                'orientation', 'tour', 'award', 'ceremony'
            ]
            
            if any(keyword in raw_title.lower() for keyword in skip_keywords):
                return None
            
            # Get date/time
            date_elem = item.find('h6')
            if not date_elem:
                return None
            
            date_text = date_elem.get_text().strip()
            
            # Skip date ranges or events with "Varies"
            if '-' in date_text and ',' in date_text.split('-')[1]:
                return None  # Date range like "Jan 1 - Dec 31"
            if 'varies' in date_text.lower():
                return None
            
            # Parse datetime
            screening_datetime = self._parse_datetime(date_text)
            if not screening_datetime:
                return None
            
            # Check if in the future
            now = datetime.now(self.pacific_tz)
            if screening_datetime < now:
                return None
            
            # Get location
            h5_tags = item.find_all('h5')
            location = None
            if len(h5_tags) > 1:
                location = h5_tags[1].get_text().strip()

            # Get poster image
            poster_url = None
            img = item.find('img')
            if img and img.get('src'):
                poster_src = img.get('src')
                if poster_src.startswith('http'):
                    poster_url = poster_src
                else:
                    poster_url = self.BASE_URL + poster_src

            # Clean title
            title = normalize_title(raw_title)

            return {
                'title': title,
                'datetime': screening_datetime,
                'ticket_url': event_url,
                'format': 'Digital',  # Default, can be updated if we find format info
                'runtime': None,
                'special_notes': location,
                'poster_url': poster_url
            }
            
        except Exception as e:
            print(f"   ⚠️  Error parsing event: {e}")
            return None
    
    def _parse_datetime(self, date_text: str) -> Optional[datetime]:
        """
        Parse date/time from USC format
        
        Examples:
            "January 12, 2026, 7:00 - 9:30 P.M."
            "January 12, 2026, 7:00 P.M."
        """
        try:
            # Remove time range, keep only start time
            # "January 12, 2026, 7:00 - 9:30 P.M." -> "January 12, 2026, 7:00 P.M."
            if ' - ' in date_text:
                parts = date_text.split(' - ')
                # Take first part and add P.M./A.M. from second part
                time_part = parts[1].strip()
                meridiem = 'P.M.' if 'P.M.' in time_part else 'A.M.'
                date_text = parts[0].strip() + ' ' + meridiem
            
            # Parse formats like "January 12, 2026, 7:00 P.M."
            # Try with period first
            for fmt in ['%B %d, %Y, %I:%M %p', '%B %d, %Y, %I:%M%p']:
                try:
                    # Clean up periods in P.M./A.M.
                    clean_text = date_text.replace('P.M.', 'PM').replace('A.M.', 'AM')
                    dt = datetime.strptime(clean_text, fmt)
                    dt_pacific = self.pacific_tz.localize(dt)
                    return dt_pacific
                except ValueError:
                    continue
            
            return None
            
        except Exception as e:
            return None