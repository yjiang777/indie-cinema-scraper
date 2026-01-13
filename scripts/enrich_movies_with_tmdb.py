"""Enrich movie database with TMDB metadata"""
import sys
from pathlib import Path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from scrapers.models.base import SessionLocal, init_db  # ← Add init_db
from scrapers.models.theater import Theater  # ← Add Theater
from scrapers.models.movie import Movie
from scrapers.models.screening import Screening  # ← Add Screening
from scrapers.tmdb_service import TMDBService

def enrich_movies():
    """Add director and metadata from TMDB to existing movies"""
    # Initialize DB first to configure all relationships
    init_db()
    
    session = SessionLocal()
    tmdb_service = TMDBService()
    
    try:
        movies = session.query(Movie).all()
        
        print(f"Enriching {len(movies)} movies with TMDB data...")
        print("="*60)
        
        updated_count = 0
        
        for i, movie in enumerate(movies, 1):
            print(f"\n[{i}/{len(movies)}] {movie.title}...", end=' ', flush=True)
            
            # Skip if already has director
            if movie.director:
                print("(already has director)")
                continue
            
            # Search TMDB
            tmdb_data = tmdb_service.search_movie(movie.title, movie.year)
            
            if tmdb_data:
                # Update movie with TMDB data
                movie.director = tmdb_data['director']
                
                # Update year if we didn't have it
                if not movie.year and tmdb_data['year']:
                    movie.year = tmdb_data['year']
                
                # Update runtime if we didn't have it
                if not movie.runtime and tmdb_data['runtime']:
                    movie.runtime = tmdb_data['runtime']
                
                session.commit()
                
                print(f"✅ Director: {tmdb_data['director']}")
                updated_count += 1
            else:
                print("❌ Not found on TMDB")
        
        print("\n" + "="*60)
        print(f"✅ Updated {updated_count} movies with director info")
        
    finally:
        session.close()


if __name__ == "__main__":
    enrich_movies()