"""Landmark Theatres scraper using their API"""
import requests
from datetime import datetime, timedelta
import pytz
from typing import List, Dict, Optional
import urllib.parse
import json

from scrapers.parsers.movie_normalizer import normalize_title, extract_format


class LandmarkAPI:
    """Scraper for Landmark Theatres using their API"""
    
    SCHEDULE_API = "https://www.landmarktheatres.com/api/gatsby-source-boxofficeapi/schedule"
    MOVIES_API = "https://www.landmarktheatres.com/api/gatsby-source-boxofficeapi/movies"
    
    def __init__(self, theater_id: str, timezone: str = "America/Los_Angeles"):
        self.theater_id = theater_id
        self.timezone = pytz.timezone(timezone)
    
    def scrape_date_range(self, start_date: datetime, end_date: datetime) -> List[Dict]:
        """
        Scrape schedule for a date range
        
        Args:
            start_date: Start date
            end_date: End date
        
        Returns:
            List of screening dictionaries
        """
        import json
        # Format dates for API (ISO format with timezone offset)
        from_str = start_date.strftime('%Y-%m-%dT%H:%M:%S')
        to_str = end_date.strftime('%Y-%m-%dT%H:%M:%S')
        
        # Build theater parameter (JSON object)
        theater_param = {
            "id": self.theater_id,
            "timeZone": str(self.timezone)
        }
        
        params = {
            'from': from_str,
            'to': to_str,
            'theaters': json.dumps(theater_param, separators=(',', ':'))
        }
        
        print(f"   Fetching schedule from API...")
        
        try:
            response = requests.get(self.SCHEDULE_API, params=params, timeout=10)
            response.raise_for_status()
            schedule_data = response.json()
        except requests.RequestException as e:
            print(f"   ❌ Error fetching schedule: {e}")
            return []
        
        if self.theater_id not in schedule_data:
            print(f"   ⚠️  No schedule data for theater {self.theater_id}")
            return []
        
        theater_schedule = schedule_data[self.theater_id].get('schedule', {})
        
        # Collect all movie IDs
        movie_ids = list(theater_schedule.keys())
        
        if not movie_ids:
            print(f"   No movies found")
            return []
        
        # Fetch movie details
        print(f"   Fetching details for {len(movie_ids)} movies...")
        movie_details = self._fetch_movie_details(movie_ids)
        
        # Parse screenings
        screenings = []
        
        for movie_id, dates in theater_schedule.items():
            movie_info = movie_details.get(movie_id, {})
            movie_title = movie_info.get('title', f'Unknown Movie {movie_id}')
            movie_runtime = movie_info.get('runtime')  # In seconds
            movie_poster = movie_info.get('poster_url')

            # Convert runtime from seconds to minutes
            runtime_minutes = int(movie_runtime / 60) if movie_runtime else None

            for date_str, showtimes in dates.items():
                for showtime in showtimes:
                    screening = self._parse_showtime(
                        showtime,
                        movie_title,
                        runtime_minutes,
                        movie_id,
                        movie_poster
                    )
                    if screening:
                        screenings.append(screening)
        
        return screenings
    
    def scrape_next_days(self, num_days: int = 14) -> List[Dict]:
        """
        Scrape the next N days
        
        Args:
            num_days: Number of days to scrape
        
        Returns:
            List of all screenings
        """
        now = datetime.now(self.timezone)
        # Set to start of day
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        end = start + timedelta(days=num_days)
        
        return self.scrape_date_range(start, end)
    
    def _fetch_movie_details(self, movie_ids: List[str]) -> Dict:
        """
        Fetch movie details from movies API

        Args:
            movie_ids: List of movie IDs

        Returns:
            Dict mapping movie_id to movie details
        """
        # Build query params with multiple ids
        params = {
            'basic': 'false',
            'castingLimit': '3'
        }

        # Add each movie ID as a separate parameter
        url_parts = [self.MOVIES_API + '?basic=false&castingLimit=3']
        for movie_id in movie_ids:
            url_parts.append(f'ids={movie_id}')

        url = url_parts[0] + '&' + '&'.join(url_parts[1:])

        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            movies_list = response.json()

            # Convert list to dict keyed by ID
            movies_dict = {}
            for movie in movies_list:
                movie_id = str(movie.get('id'))
                # Extract poster URL from images array
                images = movie.get('images', [])
                if images:
                    movie['poster_url'] = images[0].get('url')
                movies_dict[movie_id] = movie

            return movies_dict

        except requests.RequestException as e:
            print(f"   ⚠️  Error fetching movie details: {e}")
            return {}
    
    def _parse_showtime(self, showtime: Dict, movie_title: str, runtime: Optional[int], movie_id: str, poster_url: Optional[str] = None) -> Optional[Dict]:
        """Parse a single showtime"""
        try:
            # Parse datetime
            starts_at = showtime.get('startsAt')  # "2026-01-06T17:00:00"
            if not starts_at:
                return None

            dt = datetime.fromisoformat(starts_at)
            dt_with_tz = self.timezone.localize(dt)

            # Check if expired or in the past
            now = datetime.now(self.timezone)
            if dt_with_tz < now or showtime.get('isExpired', False):
                return None

            # Extract format from tags
            tags = showtime.get('tags', [])
            film_format = self._extract_format_from_tags(tags)

            # Get ticket URL
            ticket_url = self._extract_ticket_url(showtime)

            # Clean title
            title = normalize_title(movie_title)

            return {
                'title': title,
                'datetime': dt_with_tz,
                'ticket_url': ticket_url,
                'format': film_format,
                'runtime': runtime,
                'movie_id': movie_id,
                'poster_url': poster_url
            }
            
        except Exception as e:
            print(f"   ⚠️  Error parsing showtime: {e}")
            return None
    
    def _extract_format_from_tags(self, tags: List[str]) -> str:
        """Extract format from showtime tags"""
        # Check for special formats in tags
        for tag in tags:
            if '35mm' in tag.lower():
                return '35mm'
            elif '70mm' in tag.lower():
                return '70mm'
            elif 'imax' in tag.lower():
                return 'IMAX'
            elif 'digital' in tag.lower():
                return 'Digital'
        
        return 'Digital'  # Default
    
    def _extract_ticket_url(self, showtime: Dict) -> Optional[str]:
        """Extract ticket purchase URL"""
        ticketing = showtime.get('data', {}).get('ticketing', [])
        
        if ticketing and len(ticketing) > 0:
            urls = ticketing[0].get('urls', [])
            if urls:
                return urls[0]
        
        return None