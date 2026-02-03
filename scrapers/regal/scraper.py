"""Regal Theatres scraper using Playwright"""
from scrapers.base.playwright_scraper import PlaywrightScraper
from bs4 import BeautifulSoup
import json
import time
from datetime import datetime, timedelta
import pytz
from typing import List, Dict, Optional


class RegalScraper:
    """Scraper for Regal Theatres using Playwright"""
    
    def __init__(self, theater_url: str, theater_code: str, timezone: str = "America/Los_Angeles"):
        self.theater_url = theater_url
        self.theater_code = theater_code
        self.timezone = pytz.timezone(timezone)
    
    def scrape_schedule(self, days_ahead: int = 14) -> List[Dict]:
        """Scrape showtimes from Regal theater page for multiple days"""
        all_screenings = []
        today = datetime.now(self.timezone).date()

        with PlaywrightScraper(headless=True) as scraper:
            for i in range(days_ahead):
                date = today + timedelta(days=i)
                date_str = date.strftime('%m-%d-%Y')  # Regal uses MM-DD-YYYY format

                screenings = self._scrape_date(scraper, date_str)
                all_screenings.extend(screenings)

                # Small delay between requests to avoid rate limiting
                if i < days_ahead - 1:
                    time.sleep(1)

        print(f"   Extracted {len(all_screenings)} total screenings")
        return all_screenings

    def _scrape_date(self, scraper: PlaywrightScraper, date_str: str) -> List[Dict]:
        """Scrape showtimes for a specific date"""
        screenings = []
        url = f"{self.theater_url}?date={date_str}"

        print(f"   Loading {date_str}...", end='', flush=True)

        try:
            scraper.navigate_and_wait(url)
            html = scraper.get_page_content()
            soup = BeautifulSoup(html, 'html.parser')

            # Extract Next.js data
            next_data = soup.find('script', id='__NEXT_DATA__')

            if not next_data:
                print(" ❌ No data")
                return []

            data = json.loads(next_data.string)
            page_props = data.get('props', {}).get('pageProps', {})

            # Build poster lookup from movies data
            poster_lookup = self._build_poster_lookup(page_props.get('movies', []))

            # Get showtimes for this specific date
            showtimes_data = page_props.get('showtimes', [])

            if not showtimes_data:
                print(" 0 films")
                return []

            # Usually the first day in the response is the requested date
            day_data = showtimes_data[0] if showtimes_data else {}
            films = day_data.get('Film', [])

            for film in films:
                title = film.get('Title', '')
                performances = film.get('Performances', [])
                poster_url = poster_lookup.get(title)

                for performance in performances:
                    screening = self._parse_performance(title, performance, poster_url)
                    if screening:
                        screenings.append(screening)

            print(f" {len(screenings)} screenings")

        except json.JSONDecodeError as e:
            print(f" ❌ JSON error")
        except Exception as e:
            print(f" ❌ Error: {e}")

        return screenings

    def _build_poster_lookup(self, movies: List[Dict]) -> Dict[str, str]:
        """Build a lookup from movie title to poster URL"""
        lookup = {}
        for movie in movies:
            title = movie.get('Title', '')
            media = movie.get('Media', [])
            # Find poster image in media array
            for item in media:
                if item.get('Type') == 'Image' and 'Poster' in item.get('SubType', ''):
                    lookup[title] = item.get('Url') or item.get('SecureUrl')
                    break
        return lookup
    
    def _parse_performance(self, title: str, performance: Dict, poster_url: Optional[str] = None) -> Optional[Dict]:
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

            # Filter out shows that have already started (more than 30 min ago)
            now = datetime.now(self.timezone)
            time_diff = (dt_local - now).total_seconds() / 60  # minutes

            if time_diff < -30:  # Started more than 30 min ago
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
                'special_notes': ', '.join(attributes) if attributes else None,
                'poster_url': poster_url
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