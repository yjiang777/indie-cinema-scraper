"""Debug TMDB search for specific movies"""
import sys
from pathlib import Path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from scrapers.tmdb_service import TMDBService

tmdb = TMDBService()

test_movies = [
    ("THE REMAINS OF THE DAY (1993)", 1993),
    ("SHAKESPEARE WALLAH (1965)", 1965),
    ("THE GOLDEN BOWL (2000)", 2000)
]

for title, year in test_movies:
    print(f"\n{'='*60}")
    print(f"Original: {title}")
    
    # Try as-is
    result = tmdb.search_movie(title, year)
    if result:
        print(f"✅ Found: {result['title']} ({result['year']}) - {result['director']}")
    else:
        print("❌ Not found as-is")
        
        # Try lowercased
        title_lower = title.lower().title()  # "The Remains Of The Day (1993)"
        result = tmdb.search_movie(title_lower, year)
        if result:
            print(f"✅ Found with title case: {result['title']} ({result['year']}) - {result['director']}")
        else:
            print("❌ Still not found")