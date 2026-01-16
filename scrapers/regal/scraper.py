"""Regal Theatres scraper using Playwright"""
from scrapers.base.playwright_scraper import PlaywrightScraper
from bs4 import BeautifulSoup
import json
import time
from datetime import datetime
import pytz
from typing import List, Dict, Optional


class RegalScraper:
    """Scraper for Regal Theatres using Playwright"""
    
    def __init__(self, theater_url: str, theater_code: str, timezone: str = "America/Los_Angeles"):
        self.theater_url = theater_url
        self.theater_code = theater_code
        self.timezone = pytz.timezone(timezone)
    
    def scrape_schedule(self, days_ahead: int = 7) -> List[Dict]:
        """Scrape showtimes from Regal theater page"""
        screenings = []
        
        with PlaywrightScraper(headless=True) as scraper:
            print(f"   Loading page: {self.theater_url}")
            
            # Just load the base page - it has multiple days already
            scraper.navigate_and_wait(self.theater_url)
            html = scraper.get_page_content()
            soup = BeautifulSoup(html, 'html.parser')
            
            # Extract Next.js data
            next_data = soup.find('script', id='__NEXT_DATA__')
            
            if not next_data:
                print("   ❌ Could not find __NEXT_DATA__")
                return []
            
            try:
                data = json.loads(next_data.string)
                
                # The base page already has showtimes for multiple days
                showtimes_data = data.get('props', {}).get('pageProps', {}).get('showtimes', [])
                
                if not showtimes_data:
                    print("   ⚠️  No showtimes found")
                    return []
                
                print(f"   Found {len(showtimes_data)} days of showtimes")
                
                # Parse each day (limit to days_ahead)
                for day in showtimes_data[:days_ahead]:
                    films = day.get('Film', [])
                    
                    for film in films:
                        title = film.get('Title', '')
                        performances = film.get('Performances', [])
                        
                        for performance in performances:
                            screening = self._parse_performance(title, performance)
                            if screening:
                                screenings.append(screening)
                
                print(f"   Extracted {len(screenings)} screenings")
                
            except json.JSONDecodeError as e:
                print(f"   ❌ Error parsing JSON: {e}")
                return []
        
        return screenings
    
    def _parse_performance(self, title: str, performance: Dict) -> Optional[Dict]:
        """Parse a single performance/showtime"""
        try:
            # Get showtime
            showtime_str = performance.get('CalendarShowTime')
            if not showtime_str:
                return None
            
            # Parse datetime
            dt = datetime.fromisoformat(showtime_str.replace('Z', '+00:00'))
            
            # Convert to theater timezone
            if dt.tzinfo is None:
                dt_local = self.timezone.localize(dt)
            else:
                dt_local = dt.astimezone(self.timezone)
            
            # Keep shows from the next 24 hours OR shows that started within last 30 minutes
            now = datetime.now(self.timezone)
            time_diff = (dt_local - now).total_seconds() / 60  # minutes
            
            # Filter: keep if show is within [-30 min, +24 hours]
            if time_diff < -30:  # Started more than 30 min ago
                return None
            
            if time_diff > 24 * 60:  # More than 24 hours away
                return None
            
            # Extract format from attributes
            attributes = performance.get('PerformanceAttributes', [])
            film_format = self._extract_format(attributes)
            
            # Build ticket URL
            performance_id = performance.get('PerformanceId')
            ticket_url = f"https://www.regmovies.com/movies/{performance_id}" if performance_id else None
            
            return {
                'title': title,
                'datetime': dt_local,
                'ticket_url': ticket_url,
                'format': film_format,
                'runtime': None,
                'special_notes': ', '.join(attributes) if attributes else None
            }
            
        except Exception as e:
            print(f"   ⚠️  Error parsing performance for {title}: {e}")
            return None
    
    def _extract_format(self, attributes: List[str]) -> str:
        """Extract film format from performance attributes"""
        # Priority order for format detection
        if 'IMAX' in attributes:
            return 'IMAX'
        elif '70mm' in attributes:
            return '70mm'
        elif '35mm' in attributes:
            return '35mm'
        elif 'RPX' in attributes:  # Regal Premium Experience
            return 'RPX'
        elif '4DX' in attributes:
            return '4DX'
        elif 'ScreenX' in attributes:
            return 'ScreenX'
        elif '3D' in attributes:
            return '3D'
        else:
            return 'Digital'