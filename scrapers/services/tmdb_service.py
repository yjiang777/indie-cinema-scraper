"""TMDB API service for enriching movie data"""
import requests
import os
import re
from rapidfuzz import fuzz

class TMDBService:
    """Service for interacting with The Movie Database API"""
    
    def __init__(self):
        self.api_key = os.environ.get('TMDB_API_KEY')
        if not self.api_key:
            raise ValueError("TMDB_API_KEY environment variable not set")
        
        self.base_url = "https://api.themoviedb.org/3"
    
    def search_movie(self, title: str, year: int = None) -> dict:
        """Search for a movie with improved title matching"""
        try:
            # Extract year from title if present (e.g., "Movie (1993)")
            clean_title, extracted_year = self._extract_year(title)
            if extracted_year and not year:
                year = extracted_year

            # Clean the title
            clean_title = self._clean_title(clean_title)

            # Try exact search first
            result = self._try_search(clean_title, year)
            if result:
                return result

            # Try without year
            if year:
                result = self._try_search(clean_title, None)
                if result:
                    return result

            # Try removing common suffixes
            for suffix in [' 3D', ' IMAX', ' 2D', ' 70MM', ' 35MM']:
                if suffix.lower() in clean_title.lower():
                    cleaned = clean_title.replace(suffix, '').replace(suffix.lower(), '').strip()
                    result = self._try_search(cleaned, year)
                    if result:
                        return result

            # Try removing anything in parentheses
            if '(' in clean_title:
                base_title = clean_title.split('(')[0].strip()
                result = self._try_search(base_title, year)
                if result:
                    return result

            return None

        except Exception as e:
            print(f"Error searching TMDB: {e}")
            return None
    
    def _clean_title(self, title: str) -> str:
        """Clean up movie title for better matching"""
        cleaned = title.strip()

        # Handle double features - take the first movie
        if ' / ' in cleaned:
            cleaned = cleaned.split(' / ')[0].strip()

        # Remove language tags like (Telugu), (Hindi), (Arabic)
        cleaned = re.sub(r'\s*\([A-Za-z]+\)\s*$', '', cleaned)

        # Remove suffixes
        suffixes_to_remove = [
            r'\s*-\s*Early Access$',
            r'\s*\(Reissue\)$',
            r'\s*\(In Person\)$',
            r'\s*\(Cinematographer In Person\)$',
            r'\s*-\s*Hong Kong Cinema Classics$',
        ]
        for pattern in suffixes_to_remove:
            cleaned = re.sub(pattern, '', cleaned, flags=re.IGNORECASE)

        # Extract from "PREFIX: MOVIE" patterns
        prefix_patterns = [
            r'Cinematic Void Presents (.+)',
            r'The Greg Proops Film Club Presents (.+)',
            r'JANS:\s*(.+)',
            r'Met Op:\s*(.+)',
            r'IMAX:\s*(.+)',
            r'3D:\s*(.+)',
            r'70mm:\s*(.+)',
        ]
        for pattern in prefix_patterns:
            match = re.match(pattern, cleaned, re.IGNORECASE)
            if match:
                cleaned = match.group(1).strip()
                break

        # Convert from ALL CAPS
        if cleaned.isupper() and len(cleaned) > 3:
            cleaned = cleaned.title()

        return cleaned

    def _extract_year(self, title: str) -> tuple:
        """Extract year from title like 'Movie (1993)' or 'Movie (2026)'"""
        match = re.search(r'\((\d{4})\)', title)
        if match:
            year = int(match.group(1))
            clean_title = re.sub(r'\s*\(\d{4}\)', '', title).strip()
            return clean_title, year
        return title, None

    
    def _try_search(self, title: str, year: int = None, use_fuzzy: bool = True) -> dict:
        """Try a single search with given title and year"""
        try:
            params = {
                'api_key': self.api_key,
                'query': title
            }
            
            if year:
                params['year'] = year
            
            response = requests.get(f"{self.base_url}/search/movie", params=params)
            data = response.json()
            
            results = data.get('results', [])
            
            if not results:
                return None
            
            # Prefer results with higher popularity if no year specified
            if not year and len(results) > 1:
                # Sort by popularity (descending)
                results = sorted(results, key=lambda x: x.get('popularity', 0), reverse=True)
            
            # If fuzzy matching enabled, find best match
            if use_fuzzy and len(results) > 1:
                best_match = None
                best_score = 0
                
                for movie in results[:5]:  # Check top 5 results
                    movie_title = movie.get('title', '')
                    # Try multiple fuzzy matching strategies
                    score = max(
                        fuzz.ratio(title.lower(), movie_title.lower()),
                        fuzz.partial_ratio(title.lower(), movie_title.lower()),
                        fuzz.token_sort_ratio(title.lower(), movie_title.lower())
                    )
                    
                    # Boost score if it's more popular
                    popularity_boost = min(movie.get('popularity', 0) / 100, 5)
                    score += popularity_boost
                    
                    if score > best_score:
                        best_score = score
                        best_match = movie
                
                # Use best match if score is decent (>= 80)
                if best_match and best_score >= 80:
                    movie = best_match
                else:
                    movie = results[0]  # Fallback to first (most popular) result
            else:
                movie = results[0]
            
            # Build poster URL
            poster_url = None
            if movie.get('poster_path'):
                poster_url = f"https://image.tmdb.org/t/p/w500{movie['poster_path']}"
            
            return {
                'tmdb_id': movie.get('id'),
                'title': movie.get('title'),
                'director': self.get_director(movie.get('id')),
                'runtime': movie.get('runtime'),
                'poster_url': poster_url
            }
            
        except Exception as e:
            return None
    
    def get_director(self, movie_id: int) -> str:
        """Get the director for a movie by its TMDB ID"""
        try:
            params = {'api_key': self.api_key}
            
            response = requests.get(
                f"{self.base_url}/movie/{movie_id}/credits",
                params=params
            )
            data = response.json()
            
            crew = data.get('crew', [])
            
            for person in crew:
                if person.get('job') == 'Director':
                    return person.get('name')
            
            return None
            
        except Exception as e:
            print(f"Error getting director: {e}")
            return None

    def search_tv_show(self, title: str) -> dict:
        """Search for a TV show and return details including poster"""
        try:
            # Clean the title - extract show name before season/episode info
            show_name = self._extract_show_name(title)
            
            params = {
                'api_key': self.api_key,
                'query': show_name
            }
            
            response = requests.get(f"{self.base_url}/search/tv", params=params)
            data = response.json()
            
            results = data.get('results', [])
            
            if results:
                show = results[0]
                
                # Build poster URL
                poster_url = None
                if show.get('poster_path'):
                    poster_url = f"https://image.tmdb.org/t/p/w500{show['poster_path']}"
                
                # Get creator
                creator = self.get_tv_creator(show.get('id'))
                
                return {
                    'tmdb_id': show.get('id'),
                    'title': show.get('name'),
                    'director': f"TV: {creator}" if creator else "TV Series",
                    'poster_url': poster_url
                }
            
            return None
            
        except Exception as e:
            print(f"Error searching TV: {e}")
            return None

    def _extract_show_name(self, title: str) -> str:
        """Extract show name from episode title"""
        # Handle patterns like "TWIN PEAKS: Season 1, Ep. 3"
        if ':' in title:
            show_name = title.split(':')[0].strip()
            return show_name
        return title

    def get_tv_creator(self, tv_id: int) -> str:
        """Get the creator for a TV show by its TMDB ID"""
        try:
            params = {'api_key': self.api_key}
            
            response = requests.get(
                f"{self.base_url}/tv/{tv_id}",
                params=params
            )
            data = response.json()
            
            creators = data.get('created_by', [])
            
            if creators:
                return creators[0].get('name')
            
            return None
            
        except Exception as e:
            return None 