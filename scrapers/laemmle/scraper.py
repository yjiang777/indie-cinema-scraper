"""Laemmle Theatres scraper"""
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import pytz
from typing import List, Dict, Optional
import re

from scrapers.parsers.movie_normalizer import normalize_title, extract_format


class LaemmleScraper:
    """Scraper for Laemmle Theatres"""
    
    def __init__(self, theater_url: str, theater_name: str):
        self.theater_url = theater_url
        self.theater_name = theater_name
        self.base_url = "https://www.laemmle.com"
        self.pacific_tz = pytz.timezone('America/Los_Angeles')
    
    def scrape_date(self, date_str: str) -> List[Dict]:
        """
        Scrape showtimes for a specific date
        
        Args:
            date_str: Date in format 'YYYY-MM-DD' (e.g., '2026-01-07')
        
        Returns:
            List of screening dictionaries
        """
        url = f"{self.theater_url}?date={date_str}"
        print(f"   Fetching: {url}")
        
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
        except requests.RequestException as e:
            print(f"   ❌ Error fetching {url}: {e}")
            return []
        
        soup = BeautifulSoup(response.text, 'html.parser')
        screenings = []
        
        # Find all parent divs that contain film info + showtimes
        info_divs = soup.find_all('div', class_='info')
        
        for info_div in info_divs:
            # Get film info
            film_wrapper = info_div.select_one('div.film-info-wrapper')
            if not film_wrapper:
                continue
            
            # Extract title
            title_elem = film_wrapper.select_one('div.title a')
            if not title_elem:
                continue
            
            raw_title = title_elem.get_text().strip()
            title = normalize_title(raw_title)
            film_url = title_elem.get('href', '')
            if film_url and not film_url.startswith('http'):
                film_url = self.base_url + film_url
            
            # Extract runtime and rating
            detail_elem = film_wrapper.select_one('div.detail')
            runtime = None
            rating = None
            
            if detail_elem:
                detail_text = detail_elem.get_text().strip()
                # Parse "113 min. R"
                runtime_match = re.search(r'(\d+)\s*min', detail_text)
                if runtime_match:
                    runtime = int(runtime_match.group(1))
                
                # Extract rating (G, PG, PG-13, R, NC-17, NR)
                rating_match = re.search(r'\b(G|PG-13|PG|R|NC-17|NR)\b', detail_text)
                if rating_match:
                    rating = rating_match.group(1)
            
            # Get showtimes
            showtimes_div = info_div.select_one('div.showtimes')
            if not showtimes_div:
                continue
            
            # Find all showtime elements (skip past ones)
            showtime_elements = showtimes_div.find_all('div', class_='showtime')
            
            for showtime_elem in showtime_elements:
                # Skip past showtimes
                classes = showtime_elem.get('class', [])
                if 'engagement-3d-past' in classes or 'showtime-past' in ' '.join(classes):
                    continue
                
                # Extract time text
                time_text = showtime_elem.get_text().strip()
                if not time_text:
                    continue
                
                # Parse time
                screening_datetime = self._parse_datetime(date_str, time_text)
                if not screening_datetime:
                    continue
                
                # Check if screening is in the future
                now = datetime.now(self.pacific_tz)
                if screening_datetime < now:
                    continue
                
                # Extract format from full page text (may not be present)
                film_format = extract_format(info_div.get_text())
                
                screenings.append({
                    'title': title,
                    'datetime': screening_datetime,
                    'ticket_url': film_url,  # Use film page as ticket URL
                    'format': film_format,
                    'runtime': runtime,
                    'rating': rating
                })
        
        return screenings
    
    def scrape_multiple_dates(self, num_days: int = 7) -> List[Dict]:
        """
        Scrape showtimes for the next N days
        
        Args:
            num_days: Number of days to scrape (default 7)
        
        Returns:
            List of all screenings across all dates
        """
        all_screenings = []
        today = datetime.now(self.pacific_tz).date()
        
        for i in range(num_days):
            date = today + timedelta(days=i)
            date_str = date.strftime('%Y-%m-%d')
            
            screenings = self.scrape_date(date_str)
            all_screenings.extend(screenings)
            
            print(f"   Found {len(screenings)} screenings for {date_str}")
        
        return all_screenings
    
    def _parse_datetime(self, date_str: str, time_str: str) -> Optional[datetime]:
        """
        Parse date and time into datetime object
        
        Args:
            date_str: Date in format 'YYYY-MM-DD'
            time_str: Time like '7:30pm', '1:20pm'
        
        Returns:
            datetime object in Pacific timezone, or None if parsing fails
        """
        try:
            # Clean time string
            time_str = time_str.strip().lower()
            
            # Parse time
            time_match = re.match(r'(\d{1,2}):(\d{2})\s*(am|pm)', time_str)
            if not time_match:
                return None
            
            hour = int(time_match.group(1))
            minute = int(time_match.group(2))
            meridiem = time_match.group(3)
            
            # Convert to 24-hour format
            if meridiem == 'pm' and hour != 12:
                hour += 12
            elif meridiem == 'am' and hour == 12:
                hour = 0
            
            # Combine date and time
            date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
            dt = datetime.combine(date_obj, datetime.min.time().replace(hour=hour, minute=minute))
            
            # Localize to Pacific timezone
            dt_pacific = self.pacific_tz.localize(dt)
            
            return dt_pacific
            
        except Exception as e:
            print(f"   ⚠️  Error parsing datetime '{date_str} {time_str}': {e}")
            return None