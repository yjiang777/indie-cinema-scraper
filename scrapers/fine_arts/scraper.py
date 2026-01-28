"""Fine Arts Theatre Beverly Hills scraper"""
import re
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import pytz


class FineArtsScraper:
    BASE_URL = "https://fineartstheatrebh.com"
    TICKET_URL = "https://ticketing.uswest.veezi.com/sessions/?siteToken=tez3prscsvfbagchhkxbevjwk8"

    def __init__(self):
        self.theater_name = "Fine Arts Theatre Beverly Hills"
        self.theater_address = "8556 Wilshire Blvd"
        self.theater_city = "Beverly Hills"
        self.theater_state = "CA"
        self.theater_zip = "90211"
        self.theater_website = self.BASE_URL
        self.pacific_tz = pytz.timezone('America/Los_Angeles')

    def scrape_schedule(self):
        """
        Scrape the Fine Arts Theatre schedule
        Returns: List of screening dictionaries
        """
        print(f"Scraping Fine Arts Theatre from: {self.BASE_URL}")

        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
            }
            response = requests.get(self.BASE_URL, headers=headers)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, 'html.parser')
            screenings = []

            # Known movie titles from h4 tags
            movie_titles = []
            seen_titles = set()
            for h4 in soup.find_all('h4'):
                text = h4.get_text(strip=True)
                # Filter out non-movie content
                if (text and
                    len(text) > 3 and
                    len(text) < 100 and
                    text not in seen_titles and
                    not any(skip in text.lower() for skip in ['wilshire', 'grill', 'pizza', 'egg', 'dog', 'wing', 'burrito', 'pretzel', 'nacho', 'location', 'february 5', 'screenings every', '70mm'])):
                    movie_titles.append(text)
                    seen_titles.add(text)

            # Date pattern to match "Sunday, February 1st at 2:00pm"
            date_pattern = re.compile(
                r'(Sunday|Monday|Tuesday|Wednesday|Thursday|Friday|Saturday),?\s+'
                r'(January|February|March|April|May|June|July|August|September|October|November|December)\s+'
                r'(\d{1,2})(?:st|nd|rd|th)?\s+at\s+(\d{1,2}):(\d{2})\s*(am|pm)',
                re.IGNORECASE
            )

            # Get all text and pair movie titles with dates
            all_text = ' '.join(soup.stripped_strings)

            current_year = datetime.now().year

            for title in movie_titles:
                # Find the date that appears after this title
                title_pos = all_text.find(title)
                if title_pos == -1:
                    continue

                # Look for date pattern after the title
                remaining_text = all_text[title_pos:]
                match = date_pattern.search(remaining_text)

                if match:
                    day_name, month_name, day, hour, minute, ampm = match.groups()
                    hour = int(hour)
                    minute = int(minute)

                    # Convert to 24-hour format
                    if ampm.lower() == 'pm' and hour != 12:
                        hour += 12
                    elif ampm.lower() == 'am' and hour == 12:
                        hour = 0

                    # Get month number
                    months = {
                        'january': 1, 'february': 2, 'march': 3, 'april': 4,
                        'may': 5, 'june': 6, 'july': 7, 'august': 8,
                        'september': 9, 'october': 10, 'november': 11, 'december': 12
                    }
                    month = months.get(month_name.lower(), 1)

                    # Determine year
                    year = current_year
                    now = datetime.now()
                    if month < now.month or (month == now.month and int(day) < now.day):
                        year = current_year + 1

                    try:
                        dt = datetime(year, month, int(day), hour, minute)
                        dt_pacific = self.pacific_tz.localize(dt)

                        # Clean up title
                        clean_title = self._clean_title(title)

                        # Handle double features
                        if ' and ' in clean_title.lower():
                            # Split double feature
                            parts = re.split(r'\s+and\s+', clean_title, flags=re.IGNORECASE)
                            for part in parts:
                                part_clean = part.strip()
                                if part_clean:
                                    screening = {
                                        'title': part_clean,
                                        'datetime': dt_pacific,
                                        'ticket_url': self.TICKET_URL,
                                        'format': '70mm',
                                        'special_notes': '70mm Screening - Double Feature'
                                    }
                                    screenings.append(screening)
                                    print(f"   Found: {part_clean} - {dt_pacific.strftime('%b %d, %I:%M %p')}")
                        else:
                            screening = {
                                'title': clean_title,
                                'datetime': dt_pacific,
                                'ticket_url': self.TICKET_URL,
                                'format': '70mm',
                                'special_notes': '70mm Screening'
                            }
                            screenings.append(screening)
                            print(f"   Found: {clean_title} - {dt_pacific.strftime('%b %d, %I:%M %p')}")

                    except ValueError as e:
                        print(f"   Error parsing date: {e}")

            print(f"Extracted {len(screenings)} screenings")
            return screenings

        except Exception as e:
            print(f"Error scraping Fine Arts Theatre: {e}")
            return []

    def _clean_title(self, title):
        """Clean up movie title"""
        # Remove common prefixes/suffixes
        title = re.sub(r'^(IN PERSON|SPECIAL EVENT|70MM)\s*', '', title, flags=re.IGNORECASE)
        title = title.strip()
        return title

    def get_theater_info(self):
        """Return theater information"""
        return {
            'name': self.theater_name,
            'address': self.theater_address,
            'city': self.theater_city,
            'state': self.theater_state,
            'zip_code': self.theater_zip,
            'website': self.theater_website,
            'latitude': 34.0620,
            'longitude': -118.3842
        }
