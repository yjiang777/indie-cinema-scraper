"""Main scraper runner"""
import os
import sys
from pathlib import Path
from datetime import datetime
import pytz

pacific_tz = pytz.timezone('America/Los_Angeles')

from scrapers.models.base import engine, SessionLocal, init_db
from scrapers.models.theater import Theater
from scrapers.models.movie import Movie
from scrapers.models.screening import Screening
from scrapers.services.tmdb_service import TMDBService

from scrapers.new_beverly.scraper import NewBeverlyScraper

# Initialize TMDB service for movie enrichment
tmdb_service = TMDBService()
from scrapers.laemmle.scraper import LaemmleScraper
from scrapers.laemmle.theaters import LAEMMLE_THEATERS


def ensure_database_exists():
    """Ensure database directory exists"""
    db_dir = Path('database')
    db_dir.mkdir(exist_ok=True)


def run_migrations():
    """Run database migrations"""
    from sqlalchemy import text, inspect

    try:
        inspector = inspect(engine)
        tables = inspector.get_table_names()

        # Only run if theaters table exists
        if 'theaters' not in tables:
            return

        columns = [col['name'] for col in inspector.get_columns('theaters')]

        # Add description column if it doesn't exist
        if 'description' not in columns:
            with engine.connect() as conn:
                conn.execute(text('ALTER TABLE theaters ADD COLUMN description TEXT'))
                conn.commit()
                print("Migration: Added description column to theaters")
    except Exception as e:
        print(f"Migration warning: {e}")


def populate_theater_descriptions():
    """Populate theater descriptions if empty"""
    try:
        descriptions = {
        'New Beverly Cinema': 'A beloved Los Angeles repertory cinema owned by Quentin Tarantino, showing classic films on 35mm.',
        'American Cinematheque - Aero Theatre': 'Historic Art Deco theater in Santa Monica presenting classic and contemporary films.',
        'American Cinematheque - Egyptian Theatre': 'Iconic Hollywood Boulevard landmark showcasing curated film programs.',
        'American Cinematheque - Los Feliz 3': 'Three-screen venue featuring independent, foreign, and repertory films.',
        'Laemmle Royal': 'Arthouse cinema dedicated to independent and foreign films in West LA.',
        'Laemmle Monica Film Center': 'Santa Monica arthouse cinema showing independent and documentary films.',
        'Laemmle Glendale': 'Glendale location featuring art house and international cinema.',
        'Laemmle NoHo 7': 'North Hollywood venue dedicated to indie and foreign films.',
        'Laemmle Town Center 5': 'Encino theater showcasing independent and international cinema.',
        'Laemmle Newhall': 'Santa Clarita arthouse theater bringing indie films to the valley.',
        'Landmark Nuart Theatre': 'West LA repertory cinema known for midnight movies and cult classics.',
        'USC School of Cinematic Arts': 'University screening room featuring student films and classic cinema.',
        'Fine Arts Theatre Beverly Hills': 'Historic single-screen theater showing first-run and classic films.',
        'Regal LA Live Stadium 14': 'Premium multiplex at LA Live with IMAX and stadium seating.',
        'Regal Edwards Long Beach Stadium 26': 'Large format cinema with IMAX and 4DX experiences.',
        'Regal Alhambra Renaissance Stadium 14': 'Modern stadium theater serving the San Gabriel Valley.',
        'Regal Paseo Stadium 14': 'Pasadena multiplex with premium large format screens.',
        'Regal Garden Grove': 'Orange County location with stadium seating.',
    }

        session = SessionLocal()
        updated = 0
        for theater in session.query(Theater).all():
            if theater.name in descriptions and not theater.description:
                theater.description = descriptions[theater.name]
                updated += 1
        if updated:
            session.commit()
            print(f"Updated {updated} theater descriptions")
        session.close()
    except Exception as e:
        print(f"Theater descriptions warning: {e}")


def get_or_create_theater(session, name, address, city, state, website, latitude=None, longitude=None):
    """Get existing theater or create new one"""
    theater = session.query(Theater).filter_by(name=name).first()

    if not theater:
        theater = Theater(
            name=name,
            address=address,
            city=city,
            state=state,
            website=website,
            latitude=latitude,
            longitude=longitude
        )
        session.add(theater)
        session.commit()
        print(f"✅ Created theater: {name}")
    else:
        # Update coordinates if provided and not already set
        if latitude and longitude and (not theater.latitude or not theater.longitude):
            theater.latitude = latitude
            theater.longitude = longitude
            session.commit()
        print(f"♻️  Using existing theater: {name}")

    return theater


def get_or_create_movie(session, title, runtime=None, movie_format=None):
    """Get existing movie or create new one, enrich with TMDB data"""
    movie = session.query(Movie).filter_by(title=title).first()

    if not movie:
        movie = Movie(
            title=title,
            runtime=runtime,
            format=movie_format
        )
        session.add(movie)
        session.commit()

        # Enrich with TMDB data immediately
        try:
            is_tv = any(kw in title.upper() for kw in ['SEASON', 'EPISODE', 'EP.', 'WELCOME TO DERRY'])
            if is_tv:
                tmdb_data = tmdb_service.search_tv_show(title)
            else:
                tmdb_data = tmdb_service.search_movie(title)

            if tmdb_data:
                movie.director = tmdb_data.get('director')
                movie.poster_url = tmdb_data.get('poster_url')
                movie.tmdb_id = tmdb_data.get('tmdb_id')
                if not movie.runtime and tmdb_data.get('runtime'):
                    movie.runtime = tmdb_data.get('runtime')
                session.commit()
                print(f"   Created movie: {title} ✓")
            else:
                print(f"   Created movie: {title} (no poster)")
        except Exception as e:
            print(f"   Created movie: {title} (TMDB error)")

    return movie


def save_screening(session, movie, theater, screening_data):
    """Save screening to database (skip duplicates)"""
    # Get the datetime and convert to naive Pacific time for storage
    dt = screening_data['datetime']
    if dt.tzinfo is not None:
        # Convert to Pacific then remove timezone info for storage
        dt = dt.astimezone(pacific_tz).replace(tzinfo=None)

    # Check if screening already exists
    existing = session.query(Screening).filter_by(
        movie_id=movie.id,
        theater_id=theater.id,
        screening_datetime=dt
    ).first()

    if existing:
        return False  # Already exists

    # Create new screening
    screening = Screening(
        movie_id=movie.id,
        theater_id=theater.id,
        screening_datetime=dt,
        ticket_url=screening_data.get('ticket_url'),
        special_notes=screening_data.get('special_notes')
    )
    
    session.add(screening)
    session.commit()
    
    return True  # Created


def show_summary(session):
    """Display database summary"""
    theater_count = session.query(Theater).count()
    movie_count = session.query(Movie).count()
    screening_count = session.query(Screening).count()
    
    print("\n" + "="*60)
    print("📊 DATABASE SUMMARY")
    print("="*60)
    print(f"🎭 Theaters: {theater_count}")
    print(f"🎬 Movies: {movie_count}")
    print(f"🎫 Screenings: {screening_count}")
    
    # Show next 3 upcoming screenings per theater
    pacific_tz = pytz.timezone('America/Los_Angeles')
    now = datetime.now(pacific_tz)
    
    print("\n📅 Upcoming Screenings by Theater:")
    print("="*60)
    
    theaters = session.query(Theater).order_by(Theater.name).all()
    
    for theater in theaters:
        upcoming = session.query(Screening).join(Movie)\
            .filter(Screening.theater_id == theater.id)\
            .filter(Screening.screening_datetime >= now)\
            .order_by(Screening.screening_datetime)\
            .limit(3)\
            .all()
        
        if upcoming:
            print(f"\n🎭 {theater.name}")
            for screening in upcoming:
                dt = screening.screening_datetime.strftime("%a %b %d, %I:%M %p")
                format_str = f" ({screening.movie.format})" if screening.movie.format and screening.movie.format != 'Digital' else ""
                print(f"   • {dt} - {screening.movie.title}{format_str}")
        else:
            print(f"\n🎭 {theater.name}")
            print(f"   (No upcoming screenings)")



def scrape_new_beverly(session):
    """Scrape New Beverly Cinema"""
    print("\n" + "="*60)
    print("🎬 NEW BEVERLY CINEMA SCRAPER")
    print("="*60)
    
    # Create/get theater
    theater = get_or_create_theater(
        session,
        name="New Beverly Cinema",
        address="7165 Beverly Blvd, Los Angeles, CA 90036",
        city="Los Angeles",
        state="CA",
        website="https://thenewbev.com"
    )
    
    # Scrape schedule
    scraper = NewBeverlyScraper()
    print("\n🔍 Scraping schedule...")
    screenings = scraper.scrape_schedule()
    print(f"Extracted {len(screenings)} screenings\n")
    
    # Save to database
    print(f"💾 Saving {len(screenings)} screenings to database...")
    new_count = 0
    
    for screening_data in screenings:
        movie = get_or_create_movie(
            session,
            title=screening_data['title'],
            runtime=screening_data.get('runtime'),
            movie_format=screening_data.get('format')
        )
        
        if save_screening(session, movie, theater, screening_data):
            print(f"   ✅ Saved: {screening_data['title']} - {screening_data['datetime'].strftime('%b %d, %I:%M %p')}")
            new_count += 1
    
    print(f"\n✅ Added {new_count} new screenings")


def scrape_laemmle(session):
    """Scrape all Laemmle Theatres"""
    print("\n" + "="*60)
    print("🎬 LAEMMLE THEATRES SCRAPER (6 locations)")
    print("="*60)
    
    total_new_screenings = 0
    total_scraped = 0
    
    for i, theater_info in enumerate(LAEMMLE_THEATERS, 1):
        # Create/get theater (quietly)
        theater = get_or_create_theater(
            session,
            name=theater_info['name'],
            address=theater_info['address'],
            city=theater_info['city'],
            state=theater_info['state'],
            website=theater_info['url']
        )
        
        # Scrape schedule
        print(f"\n[{i}/{len(LAEMMLE_THEATERS)}] {theater_info['name']}...", end='', flush=True)
        
        scraper = LaemmleScraper(theater_info['url'], theater_info['name'])
        screenings = scraper.scrape_multiple_dates(num_days=14)
        
        print(f" {len(screenings)} screenings", end='', flush=True)
        
        # Save to database (quietly)
        new_count = 0
        for screening_data in screenings:
            movie = get_or_create_movie(
                session,
                title=screening_data['title'],
                runtime=screening_data.get('runtime'),
                movie_format=screening_data.get('format')
            )
            
            if save_screening(session, movie, theater, screening_data):
                new_count += 1
        
        total_scraped += len(screenings)
        total_new_screenings += new_count
        
        print(f" → {new_count} new")
    
    print(f"\n{'='*60}")
    print(f"✅ Laemmle: {total_new_screenings} new screenings (scraped {total_scraped} total)")
    print(f"{'='*60}")

def scrape_american_cinematheque(session):
    """Scrape American Cinematheque theaters"""
    print("\n" + "="*60)
    print("🎬 AMERICAN CINEMATHEQUE SCRAPER")
    print("="*60)
    
    from scrapers.american_cinematheque.scraper import AmericanCinemathequeAPI
    from scrapers.american_cinematheque.theaters import AMERICAN_CINEMATHEQUE_THEATERS
    
    # Create theaters in database
    theaters_by_id = {}
    for theater_info in AMERICAN_CINEMATHEQUE_THEATERS:
        theater = get_or_create_theater(
            session,
            name=theater_info['name'],
            address=theater_info['address'],
            city=theater_info['city'],
            state=theater_info['state'],
            website="https://www.americancinematheque.com"
        )
        theaters_by_id[theater_info['api_id']] = theater
    
    # Scrape next 14 days
    api = AmericanCinemathequeAPI()
    print("\n🔍 Scraping next 14 days from API...")
    screenings = api.scrape_next_days(num_days=14)
    
    print(f"\n💾 Saving {len(screenings)} screenings to database...")
    new_count = 0
    
    for screening_data in screenings:
        # Get theater from API ID
        theater_id = screening_data.get('theater_id')
        theater = theaters_by_id.get(theater_id)
        
        if not theater:
            print(f"   ⚠️  Unknown theater ID: {theater_id}")
            continue
        
        # Create movie
        movie = get_or_create_movie(
            session,
            title=screening_data['title'],
            runtime=screening_data.get('runtime'),
            movie_format=screening_data.get('format')
        )
        
        # Create screening
        if save_screening(session, movie, theater, screening_data):
            new_count += 1
    
    print(f"\n✅ Added {new_count} new screenings from American Cinematheque")
def scrape_landmark(session):
    """Scrape Landmark Theatres"""
    print("\n" + "="*60)
    print("🎬 LANDMARK THEATRES SCRAPER (1 location)")
    print("="*60)
    
    from scrapers.landmark.scraper import LandmarkAPI
    from scrapers.landmark.theaters import LANDMARK_THEATERS
    
    total_new_screenings = 0
    
    for theater_info in LANDMARK_THEATERS:
        print(f"\n📍 {theater_info['name']}...", end='', flush=True)
        
        # Create/get theater
        theater = get_or_create_theater(
            session,
            name=theater_info['name'],
            address=theater_info['address'],
            city=theater_info['city'],
            state=theater_info['state'],
            website="https://www.landmarktheatres.com"
        )
        
        # Scrape schedule
        api = LandmarkAPI(theater_info['api_id'], theater_info['timezone'])
        screenings = api.scrape_next_days(num_days=14)
        
        print(f" {len(screenings)} screenings", end='', flush=True)
        
        # Save to database
        new_count = 0
        for screening_data in screenings:
            movie = get_or_create_movie(
                session,
                title=screening_data['title'],
                runtime=screening_data.get('runtime'),
                movie_format=screening_data.get('format')
            )
            
            if save_screening(session, movie, theater, screening_data):
                new_count += 1
        
        total_new_screenings += new_count
        print(f" → {new_count} new")
    
    print(f"\n{'='*60}")
    print(f"✅ Landmark: {total_new_screenings} new screenings")
    print(f"{'='*60}")
def scrape_usc_cinema(session):
    """Scrape USC Cinema"""
    print("\n" + "="*60)
    print("🎬 USC CINEMA SCRAPER")
    print("="*60)
    
    from scrapers.usc_cinema.scraper import USCCinemaScraper
    from scrapers.usc_cinema.theater import USC_CINEMA_THEATER
    
    # Create/get theater
    theater = get_or_create_theater(
        session,
        name=USC_CINEMA_THEATER['name'],
        address=USC_CINEMA_THEATER['address'],
        city=USC_CINEMA_THEATER['city'],
        state=USC_CINEMA_THEATER['state'],
        website=USC_CINEMA_THEATER['website']
    )
    
    # Scrape schedule
    scraper = USCCinemaScraper()
    print("\n🔍 Scraping schedule...")
    screenings = scraper.scrape_schedule()
    
    print(f"\n💾 Saving {len(screenings)} screenings to database...")
    new_count = 0
    
    for screening_data in screenings:
        movie = get_or_create_movie(
            session,
            title=screening_data['title'],
            runtime=screening_data.get('runtime'),
            movie_format=screening_data.get('format')
        )
        
        if save_screening(session, movie, theater, screening_data):
            new_count += 1
    
    print(f"✅ Added {new_count} new screenings from USC Cinema")

def scrape_regal(session):
    """Scrape Regal Theatres"""
    print("\n" + "="*60)
    print("🎬 REGAL THEATRES SCRAPER")
    print("="*60)

    try:
        from scrapers.regal.scraper import RegalScraper
    except ImportError:
        print("⏭️  Skipping - Playwright not installed")
        return

    from scrapers.regal.theaters import REGAL_THEATERS
    
    total_new_screenings = 0
    
    for theater_info in REGAL_THEATERS:
        print(f"\n📍 {theater_info['name']}...", end='', flush=True)
        
        # Create/get theater
        theater = get_or_create_theater(
            session,
            name=theater_info['name'],
            address=theater_info['address'],
            city=theater_info['city'],
            state=theater_info['state'],
            website=theater_info['url']
        )
        
        # Scrape schedule
        scraper = RegalScraper(
            theater_url=theater_info['url'],
            theater_code=theater_info['theater_code'],
            timezone=theater_info['timezone']
        )
        
        screenings = scraper.scrape_schedule(days_ahead=14)
        
        print(f" {len(screenings)} screenings", end='', flush=True)
        
        # Save to database
        new_count = 0
        for screening_data in screenings:
            movie = get_or_create_movie(
                session,
                title=screening_data['title'],
                runtime=screening_data.get('runtime'),
                movie_format=screening_data.get('format')
            )
            
            if save_screening(session, movie, theater, screening_data):
                new_count += 1
        
        total_new_screenings += new_count
        print(f" → {new_count} new")
    
    print(f"\n{'='*60}")
    print(f"✅ Regal: {total_new_screenings} new screenings")
    print(f"{'='*60}")

def scrape_fine_arts(session):
    """Scrape Fine Arts Theatre Beverly Hills"""
    print("\n" + "="*60)
    print("🎬 FINE ARTS THEATRE BEVERLY HILLS SCRAPER")
    print("="*60)

    from scrapers.fine_arts.scraper import FineArtsScraper

    scraper = FineArtsScraper()
    theater_info = scraper.get_theater_info()

    # Get or create theater with coordinates for map
    theater = get_or_create_theater(
        session,
        name=theater_info['name'],
        address=theater_info['address'],
        city=theater_info['city'],
        state=theater_info['state'],
        website=theater_info['website'],
        latitude=theater_info['latitude'],
        longitude=theater_info['longitude']
    )

    screenings = scraper.scrape_schedule()
    new_count = 0

    for screening_data in screenings:
        movie = get_or_create_movie(
            session,
            title=screening_data['title'],
            movie_format=screening_data.get('format')
        )

        if save_screening(session, movie, theater, screening_data):
            new_count += 1

    print(f"\n✅ Added {new_count} new screenings from Fine Arts Theatre")


def main():
    """Main scraper execution"""
    ensure_database_exists()
    init_db()
    run_migrations()
    populate_theater_descriptions()

    session = SessionLocal()

    try:
        scrape_new_beverly(session)
        scrape_laemmle(session)
        scrape_american_cinematheque(session)
        scrape_landmark(session)
        scrape_usc_cinema(session)
        scrape_fine_arts(session)

        # Playwright-based scrapers (may fail due to timeouts/blocking)
        try:
            scrape_regal(session)
        except Exception as e:
            print(f"\n⚠️  Regal scraper failed: {e}")
            print("Continuing with other scrapers...")

        show_summary(session)
        
    finally:
        session.close()


if __name__ == "__main__":
    main()