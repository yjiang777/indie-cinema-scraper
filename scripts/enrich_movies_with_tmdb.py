"""Enrich movie database with TMDB metadata"""
import sys
from pathlib import Path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from scrapers.models.base import SessionLocal, init_db  # ← Add init_db
from scrapers.models.theater import Theater  # ← Add Theater
from scrapers.models.movie import Movie
from scrapers.models.screening import Screening  # ← Add Screening
from scrapers.services.tmdb_service import TMDBService

def enrich_movies():
    """Enrich movies with TMDB data"""
    init_db()
    session = SessionLocal()
    
    # Initialize TMDB service
    tmdb_service = TMDBService()
    
    # Get all movies
    movies = session.query(Movie).all()
    
    print(f"Found {len(movies)} movies to enrich")
    print("="*60)
    
    enriched = 0  # ← Add this line
    skipped = 0   # ← Add this line
    
    for idx, movie in enumerate(movies, 1):
        print(f"[{idx}/{len(movies)}] {movie.title}... ", end='', flush=True)
        
        # Skip if already has both director AND poster
        if movie.director and movie.poster_url:
            print("(already enriched)")
            skipped += 1
            continue
        
        # Check if it's a TV episode
        is_tv = any(keyword in movie.title.upper() for keyword in ['SEASON', 'EPISODE', 'EP.', 'WELCOME TO DERRY', 'IT:'])
        
        if is_tv:
            # Search TV API
            tmdb_data = tmdb_service.search_tv_show(movie.title)
        else:
            # Search movie API
            tmdb_data = tmdb_service.search_movie(movie.title, movie.year)
        
        if tmdb_data:
            if not movie.director:
                movie.director = tmdb_data.get('director')
            if not movie.poster_url:
                movie.poster_url = tmdb_data.get('poster_url')
            if not movie.tmdb_id:
                movie.tmdb_id = tmdb_data.get('tmdb_id')
            if not movie.runtime:
                movie.runtime = tmdb_data.get('runtime')
            session.commit()
            enriched += 1
            print(f"✅")
        else:
            print("❌ Not found on TMDB")
    
    print("\n" + "="*60)
    print(f"✅ Enriched: {enriched}")
    print(f"⏭️  Skipped: {skipped}")
    print(f"❌ Not found: {len(movies) - enriched - skipped}")
    print("="*60)
    
    session.close()


if __name__ == "__main__":
    enrich_movies()