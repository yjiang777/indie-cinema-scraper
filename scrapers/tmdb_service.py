"""TMDB API integration for movie metadata"""
import tmdbsimple as tmdb
import os
from dotenv import load_dotenv
from typing import Optional, Dict, List

# Load environment variables
load_dotenv()
tmdb.API_KEY = os.getenv('TMDB_API_KEY')


class TMDBService:
    """Service for fetching movie metadata from TMDB"""
    
    @staticmethod
    def search_movie(title: str, year: Optional[int] = None) -> Optional[Dict]:
        """
        Search for a movie on TMDB
        
        Args:
            title: Movie title
            year: Optional release year for better matching
        
        Returns:
            Movie data dict or None
        """
        try:
            # Clean up title
            import re
            
            # Remove year in parentheses if present
            title_clean = re.sub(r'\s*\(\d{4}\)\s*', '', title)
            
            # Convert all-caps to title case if needed
            if title_clean.isupper():
                title_clean = title_clean.title()
            
            # Remove extra whitespace
            title_clean = ' '.join(title_clean.split())
            
            search = tmdb.Search()
            
            # Try with year first
            if year:
                response = search.movie(query=title_clean, year=year)
                if response['results']:
                    # Get the first (most relevant) result
                    movie_data = response['results'][0]
                    return TMDBService._fetch_movie_details(movie_data['id'])
            
            # Try without year
            response = search.movie(query=title_clean)
            
            if response['results']:
                # If we have a year, try to match it
                if year:
                    for result in response['results'][:3]:  # Check top 3 results
                        release_year = result.get('release_date', '')[:4]
                        if release_year == str(year):
                            return TMDBService._fetch_movie_details(result['id'])
                
                # No year match, return first result
                return TMDBService._fetch_movie_details(response['results'][0]['id'])
            
            return None
            
        except Exception as e:
            print(f"TMDB search error for '{title}': {e}")
            return None

    @staticmethod
    def _fetch_movie_details(movie_id: int) -> Dict:
        """Fetch full movie details including credits"""
        try:
            movie = tmdb.Movies(movie_id)
            details = movie.info()
            credits = movie.credits()
            
            # Extract director(s)
            directors = [
                crew['name'] 
                for crew in credits.get('crew', []) 
                if crew['job'] == 'Director'
            ]
            
            return {
                'tmdb_id': movie_id,
                'title': details.get('title'),
                'director': ', '.join(directors) if directors else None,
                'year': int(details.get('release_date', '')[:4]) if details.get('release_date') else None,
                'poster_path': details.get('poster_path'),
                'backdrop_path': details.get('backdrop_path'),
                'overview': details.get('overview'),
                'runtime': details.get('runtime'),
                'genres': [g['name'] for g in details.get('genres', [])],
                'vote_average': details.get('vote_average'),
                'cast': [
                    cast['name'] 
                    for cast in credits.get('cast', [])[:5]  # Top 5 cast
                ]
            }
        except Exception as e:
            print(f"Error fetching details for movie {movie_id}: {e}")
            return None
    
    @staticmethod
    def get_poster_url(poster_path: Optional[str], size: str = 'w500') -> Optional[str]:
        """
        Get full URL for poster image
        
        Args:
            poster_path: Poster path from TMDB
            size: Image size (w92, w154, w185, w342, w500, w780, original)
        
        Returns:
            Full URL or None
        """
        if poster_path:
            return f"https://image.tmdb.org/t/p/{size}{poster_path}"
        return None
    
    @staticmethod
    def search_movies_by_director(director_name: str, limit: int = 20) -> List[Dict]:
        """
        Search for movies by a specific director
        
        Args:
            director_name: Director's name
            limit: Maximum number of results
        
        Returns:
            List of movie titles
        """
        try:
            # Search for the person
            search = tmdb.Search()
            response = search.person(query=director_name)
            
            if not response['results']:
                return []
            
            # Get the first person (most relevant)
            person_id = response['results'][0]['id']
            
            # Get their filmography
            person = tmdb.People(person_id)
            credits = person.movie_credits()
            
            # Filter for director credits
            directed_movies = [
                {
                    'title': movie['title'],
                    'year': int(movie.get('release_date', '')[:4]) if movie.get('release_date') else None,
                    'tmdb_id': movie['id']
                }
                for movie in credits.get('crew', [])
                if movie.get('job') == 'Director'
            ]
            
            # Sort by year (newest first) and limit
            directed_movies.sort(key=lambda x: x['year'] or 0, reverse=True)
            
            return directed_movies[:limit]
            
        except Exception as e:
            print(f"TMDB director search error for '{director_name}': {e}")
            return []