"""Enrich movie database with TMDB metadata"""
import sys
import argparse
from pathlib import Path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from scrapers.models.base import SessionLocal, init_db  # ← Add init_db
from scrapers.models.theater import Theater  # ← Add Theater
from scrapers.models.movie import Movie
from scrapers.models.screening import Screening  # ← Add Screening
from scrapers.services.tmdb_service import TMDBService

def enrich_movies(force=False, retry_missing=False):
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

        # Skip if already has both director AND poster (unless force or retry_missing)
        if movie.director and movie.poster_url and not force:
            print("(already enriched)")
            skipped += 1
            continue

        # Skip if has tmdb_id but missing poster (unless retry_missing or force)
        if movie.tmdb_id and not movie.poster_url and not retry_missing and not force:
            print("(has tmdb_id, missing poster)")
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
            # When force is enabled, always update; otherwise only update if empty
            if force or not movie.director:
                movie.director = tmdb_data.get('director')
            if force or not movie.poster_url:
                movie.poster_url = tmdb_data.get('poster_url')
            if force or not movie.tmdb_id:
                movie.tmdb_id = tmdb_data.get('tmdb_id')
            if force or not movie.runtime:
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
    parser = argparse.ArgumentParser(description='Enrich movies with TMDB metadata')
    parser.add_argument('--force', action='store_true', help='Re-enrich all movies, even if already enriched')
    parser.add_argument('--retry-missing', action='store_true', help='Retry movies that have tmdb_id but missing poster')
    args = parser.parse_args()
    enrich_movies(force=args.force, retry_missing=args.retry_missing)