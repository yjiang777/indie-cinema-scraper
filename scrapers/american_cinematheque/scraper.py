"""American Cinematheque scraper using Algolia API"""
import requests
from datetime import datetime, timedelta
import pytz
from typing import List, Dict, Optional
import re
from html import unescape

from scrapers.parsers.movie_normalizer import normalize_title, extract_format


class AmericanCinemathequeAPI:
    """Scraper for American Cinematheque using their Algolia API"""
    
# Theater location ID mapping (from API)
    THEATER_IDS = {
        54: "American Cinematheque - Aero Theatre",
        55: "American Cinematheque - Egyptian Theatre",
        102: "American Cinematheque - Los Feliz 3"
    }
    
    API_URL = "https://www.americancinematheque.com/wp-json/wp/v2/algolia_get_events"
    
    def __init__(self):
        self.pacific_tz = pytz.timezone('America/Los_Angeles')
    
    def scrape_date_range(self, start_date: datetime, end_date: datetime) -> List[Dict]:
        """
        Scrape events within a date range
        
        Args:
            start_date: Start date (datetime object)
            end_date: End date (datetime object)
        
        Returns:
            List of screening dictionaries
        """
        # Convert to Unix timestamps (seconds since epoch)
        start_ts = int(start_date.timestamp())
        end_ts = int(end_date.timestamp())
        
        params = {
            'environment': 'production',
            'startDate': start_ts,
            'endDate': end_ts
        }
        
        print(f"   Fetching: {self.API_URL}")
        print(f"   Date range: {start_date.date()} to {end_date.date()}")
        
        try:
            response = requests.get(self.API_URL, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
        except requests.RequestException as e:
            print(f"   ❌ Error fetching API: {e}")
            return []
        
        if 'hits' not in data:
            print(f"   ⚠️  No 'hits' in response")
            return []
        
        screenings = []
        
        for event in data['hits']:
            screening = self._parse_event(event)
            if screening:
                screenings.append(screening)
        
        return screenings
    
    def scrape_next_days(self, num_days: int = 14) -> List[Dict]:
        """
        Scrape the next N days
        
        Args:
            num_days: Number of days to scrape (default 14)
        
        Returns:
            List of all screenings
        """
        now = datetime.now(self.pacific_tz)
        end = now + timedelta(days=num_days)
        
        return self.scrape_date_range(now, end)
    
    def _parse_event(self, event: Dict) -> Optional[Dict]:
        """Parse a single event from API response"""
        try:
            # Extract basic info
            raw_title = event.get('title', '')
            title = self._clean_title(raw_title)
            
            # Get theater
            location_ids = event.get('event_location', [])
            if not location_ids:
                return None
            
            theater_id = location_ids[0]
            theater_name = self.THEATER_IDS.get(theater_id, f"Unknown Theater (ID: {theater_id})")
            
            # Parse date and time
            date_str = event.get('event_start_date', '')  # "20260125"
            time_str = event.get('event_start_time', '')  # "17:00:00"
            
            if not date_str or not time_str:
                return None
            
            screening_datetime = self._parse_datetime(date_str, time_str)
            if not screening_datetime:
                return None
            
            # Check if in the future
            now = datetime.now(self.pacific_tz)
            if screening_datetime < now:
                return None
            
            # Get URL
            ticket_url = event.get('url', '')

            # Extract format from title or excerpt
            excerpt = event.get('event_card_excerpt', '')
            full_text = f"{raw_title} {excerpt}"
            film_format = extract_format(full_text)

            # Get runtime if available (end_time - start_time)
            end_time_str = event.get('event_end_time', '')
            runtime = self._calculate_runtime(time_str, end_time_str) if end_time_str else None

            # Get poster from event_card_image
            event_card_image = event.get('event_card_image', {})
            poster_url = event_card_image.get('url') if isinstance(event_card_image, dict) else None

            return {
                'title': title,
                'datetime': screening_datetime,
                'ticket_url': ticket_url,
                'format': film_format,
                'runtime': runtime,
                'theater_name': theater_name,
                'theater_id': theater_id,
                'special_notes': self._extract_special_notes(excerpt),
                'poster_url': poster_url
            }
            
        except Exception as e:
            print(f"   ⚠️  Error parsing event: {e}")
            return None
    
    def _clean_title(self, raw_title: str) -> str:
        """Clean movie title from API"""
        # Remove HTML entities
        title = unescape(raw_title)
        
        # Remove event type prefixes like "Masterclass / "
        title = re.sub(r'^(Masterclass|Q&A|Discussion|Screening)\s*[/\-]\s*', '', title, flags=re.IGNORECASE)
        
        # Normalize
        title = normalize_title(title)
        
        return title
    
    def _parse_datetime(self, date_str: str, time_str: str) -> Optional[datetime]:
        """
        Parse date and time from API format
        
        Args:
            date_str: "20260125" (YYYYMMDD)
            time_str: "17:00:00" (HH:MM:SS)
        
        Returns:
            datetime object in Pacific timezone
        """
        try:
            # Parse date
            year = int(date_str[:4])
            month = int(date_str[4:6])
            day = int(date_str[6:8])
            
            # Parse time
            hour, minute, second = map(int, time_str.split(':'))
            
            # Create datetime
            dt = datetime(year, month, day, hour, minute, second)
            
            # Localize to Pacific
            dt_pacific = self.pacific_tz.localize(dt)
            
            return dt_pacific
            
        except Exception as e:
            print(f"   ⚠️  Error parsing datetime '{date_str} {time_str}': {e}")
            return None
    
    def _calculate_runtime(self, start_time: str, end_time: str) -> Optional[int]:
        """Calculate runtime in minutes from start and end times"""
        try:
            start_parts = list(map(int, start_time.split(':')))
            end_parts = list(map(int, end_time.split(':')))
            
            start_minutes = start_parts[0] * 60 + start_parts[1]
            end_minutes = end_parts[0] * 60 + end_parts[1]
            
            runtime = end_minutes - start_minutes
            
            return runtime if runtime > 0 else None
            
        except:
            return None
    
    def _extract_special_notes(self, excerpt: str) -> Optional[str]:
        """Extract special notes from excerpt (Q&A, Masterclass, etc)"""
        if not excerpt:
            return None
        
        # Remove HTML tags
        text = re.sub(r'<[^>]+>', '', excerpt)
        text = unescape(text).strip()
        
        # Look for special indicators
        if any(word in text.lower() for word in ['masterclass', 'q&a', 'discussion', 'introduction']):
            # Extract the relevant part
            lines = [line.strip() for line in text.split('\n') if line.strip()]
            if len(lines) > 1:
                return lines[1]  # Usually the second line has the note
        
        return None