"""New Beverly Cinema scraper"""
import re
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from ..parsers.date_parser import parse_new_beverly_date, get_current_year
from ..parsers.movie_normalizer import normalize_title, extract_format, split_double_feature

class NewBeverlyScraper:
    BASE_URL = "https://thenewbev.com"
    SCHEDULE_URL = f"{BASE_URL}/schedule/"
    
    def __init__(self):
        self.theater_name = "New Beverly Cinema"
        self.theater_address = "7165 Beverly Blvd"
        self.theater_city = "Los Angeles"
        self.theater_state = "CA"
        self.theater_zip = "90036"
        self.theater_website = self.BASE_URL
    
    def scrape_schedule(self):
            """
            Scrape the New Beverly monthly schedule
            Returns: List of screening dictionaries
            """
            print(f"Scraping New Beverly schedule from: {self.SCHEDULE_URL}")
            
            try:
                response = requests.get(self.SCHEDULE_URL)
                response.raise_for_status()
                
                soup = BeautifulSoup(response.text, 'html.parser')
                screenings = []
                
                # Find all program links
                program_links = soup.find_all('a', href=lambda x: x and '/program/' in x)
                print(f"Found {len(program_links)} program links")
                
                current_year = get_current_year()
                
                for link in program_links:
                    try:
                        # Get URL
                        url = link.get('href')
                        if not url.startswith('http'):
                            url = self.BASE_URL + url
                        
                        # Get full text and split by lines
                        full_text = link.get_text()
                        lines = [line.strip() for line in full_text.split('\n') if line.strip()]
                        
                        # Find date components
                        # Format: ["Tue,", "January", "06", "7:30 pm", "/ 9:25 pm", "Movie Title", ...]
                        day_of_week = None
                        month = None
                        day = None
                        times = []
                        
                        for i, line in enumerate(lines):
                            # Look for day of week (ends with comma)
                            if line.endswith(','):
                                day_of_week = line
                            # Look for month
                            elif line in ['January', 'February', 'March', 'April', 'May', 'June', 
                                        'July', 'August', 'September', 'October', 'November', 'December']:
                                month = line
                            # Look for day number
                            elif line.isdigit() and int(line) <= 31:
                                day = line
                            # Look for times (contains "pm" or "am")
                            elif 'pm' in line.lower() or 'am' in line.lower():
                                # Handle format like "7:30 pm / 9:25 pm"
                                if '/' in line:
                                    time_parts = line.split('/')
                                    times.extend([t.strip() for t in time_parts if 'pm' in t or 'am' in t])
                                else:
                                    times.append(line)
                        
                        # Find movie title (h4 tag)
                        title_elem = link.find('h4')
                        if not title_elem:
                            continue
                        
                        title_text = title_elem.get_text()
                        
                        # Skip if we don't have required date components
                        if not (month and day):
                            continue
                        
                        # Build date string
                        date_text = f"{day_of_week} {month} {day}" if day_of_week else f"{month} {day}"
                        
                        # Extract format from full text
                        format_type = extract_format(full_text)
                        
                        # Handle double features
                        titles = split_double_feature(title_text)
                        
                        # If we have multiple times (double feature), match with titles
                        if len(times) > 1 and len(titles) > 1:
                            # Pair each time with each title
                            for title, time in zip(titles, times):
                                normalized_title = normalize_title(title)
                                screening_datetime = parse_new_beverly_date(date_text, time, current_year)
                                
                                if screening_datetime and normalized_title:
                                    screening = {
                                        'title': normalized_title,
                                        'datetime': screening_datetime,
                                        'ticket_url': url,
                                        'format': format_type,
                                        'special_notes': None
                                    }
                                    screenings.append(screening)
                        else:
                            # Single screening or use first time for all titles
                            time = times[0] if times else None
                            if not time:
                                continue
                            
                            for title in titles:
                                normalized_title = normalize_title(title)
                                screening_datetime = parse_new_beverly_date(date_text, time, current_year)
                                
                                if screening_datetime and normalized_title:
                                    screening = {
                                        'title': normalized_title,
                                        'datetime': screening_datetime,
                                        'ticket_url': url,
                                        'format': format_type,
                                        'special_notes': None
                                    }
                                    screenings.append(screening)
                            
                    except Exception as e:
                        print(f"Error parsing link: {e}")
                        continue
                
                print(f"Extracted {len(screenings)} screenings")
                return screenings
                
            except Exception as e:
                print(f"Error scraping New Beverly: {e}")
                return []
    
    def get_theater_info(self):
        """Return theater information"""
        return {
            'name': self.theater_name,
            'address': self.theater_address,
            'city': self.theater_city,
            'state': self.theater_state,
            'zip_code': self.theater_zip,
            'website': self.theater_website,
            'latitude': 34.0759,  # Approximate
            'longitude': -118.3432
        }