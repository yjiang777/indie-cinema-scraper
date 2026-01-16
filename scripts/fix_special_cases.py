"""Fix directors for double features and TV shows"""
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Now import from scrapers
from scrapers.models.base import SessionLocal, init_db
from scrapers.models.movie import Movie
from scrapers.models.theater import Theater
from scrapers.models.screening import Screening
from scrapers.services.tmdb_service import TMDBService
import re

init_db()
session = SessionLocal()
tmdb = TMDBService()

# Get movies without directors
movies = session.query(Movie).filter(Movie.director == None).all()

print(f"Fixing {len(movies)} movies...")
print("="*60)

for movie in movies:
    print(f"\n{movie.title}...", end=' ', flush=True)
    
    # Check if it's a double feature (contains " / ")
    if ' / ' in movie.title:
        parts = movie.title.split(' / ')
        
        if len(parts) == 2:
            print(f"\n  Double feature detected: {parts[0]} + {parts[1]}")
            
            directors = []
            
            # Search for each movie
            for part in parts:
                part_clean = part.strip()
                result = tmdb.search_movie(part_clean, movie.year)
                
                if result and result['director']:
                    print(f"    • {part_clean}: {result['director']}")
                    directors.append(result['director'])
            
            if directors:
                movie.director = ' / '.join(directors)
                session.commit()
                print(f"  ✅ Combined: {movie.director}")
            else:
                print("  ❌ Could not find directors")
            
            continue
    
    # Check if it's a TV episode (contains "Season" or "Ep.")
# Check if it's a TV episode (contains "Season" or "Ep.")
    if 'season' in movie.title.lower() or 'ep.' in movie.title.lower():
        # Extract show name (everything before "Season" or ":")
        show_match = re.match(r'([^:]+)', movie.title)
        
        if show_match:
            show_name = show_match.group(1).strip()
            print(f"\n  TV show detected: {show_name}")
            
            # Search TMDB TV database
            tv_data = tmdb.search_tv_show(show_name, movie.year)
            
            if tv_data and tv_data['creator']:
                # Store creator with special prefix to distinguish from director
                movie.director = f"TV:{tv_data['creator']}"
                session.commit()
                print(f"  ✅ Creator: {tv_data['creator']}")
            else:
                # Fallback to generic "TV Series"
                movie.director = "TV Series"
                session.commit()
                print(f"  ⚠️  Could not find creator, marked as TV Series")
            
            continue
    
    # Check for special event prefixes that contain actual movie titles
    special_patterns = [
        (r'cinematic void presents\s+(.+)', 'Cinematic Void event'),
        (r'the greg proops film club presents\s+(.+)', 'Greg Proops Film Club'),
    ]
    
    for pattern, event_type in special_patterns:
        match = re.match(pattern, movie.title, re.IGNORECASE)
        if match:
            actual_title = match.group(1).strip()
            print(f"\n  Special event: {event_type}")
            print(f"  Actual movie: {actual_title}")
            
            result = tmdb.search_movie(actual_title, movie.year)
            if result and result['director']:
                movie.director = result['director']
                session.commit()
                print(f"  ✅ Director: {result['director']}")
            else:
                print("  ❌ Could not find on TMDB")
            
            break
    else:
        # No pattern matched - likely a showcase or tribute
        if any(word in movie.title.lower() for word in ['showcase', 'tribute', 'presents']):
            print("  Special event (no director needed)")

print("\n" + "="*60)
print("✅ Fix complete!")

session.close()