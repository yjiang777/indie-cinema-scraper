"""Main scraper runner"""
import os
import sys
from pathlib import Path
from datetime import datetime
import pytz

from scrapers.models.base import engine, SessionLocal, init_db
from scrapers.models.theater import Theater
from scrapers.models.movie import Movie
from scrapers.models.screening import Screening

from scrapers.new_beverly.scraper import NewBeverlyScraper
from scrapers.laemmle.scraper import LaemmleScraper
from scrapers.laemmle.theaters import LAEMMLE_THEATERS


def ensure_database_exists():
    """Ensure database directory exists"""
    db_dir = Path('database')
    db_dir.mkdir(exist_ok=True)


def get_or_create_theater(session, name, address, city, state, website):
    """Get existing theater or create new one"""
    theater = session.query(Theater).filter_by(name=name).first()
    
    if not theater:
        theater = Theater(
            name=name,
            address=address,
            city=city,
            state=state,
            website=website
        )
        session.add(theater)
        session.commit()
        print(f"✅ Created theater: {name}")
    else:
        print(f"♻️  Using existing theater: {name}")
    
    return theater


def get_or_create_movie(session, title, runtime=None, movie_format=None):
    """Get existing movie or create new one"""
    movie = session.query(Movie).filter_by(title=title).first()
    
    if not movie:
        movie = Movie(
            title=title,
            runtime=runtime,
            format=movie_format
        )
        session.add(movie)
        session.commit()
        print(f"   Created movie: {title}")
    
    return movie


def save_screening(session, movie, theater, screening_data):
    """Save screening to database (skip duplicates)"""
    # Check if screening already exists
    existing = session.query(Screening).filter_by(
        movie_id=movie.id,
        theater_id=theater.id,
        screening_datetime=screening_data['datetime']
    ).first()
    
    if existing:
        return False  # Already exists
    
    # Create new screening
    screening = Screening(
        movie_id=movie.id,
        theater_id=theater.id,
        screening_datetime=screening_data['datetime'],
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
    print("🎬 LAEMMLE THEATRES SCRAPER (7 locations)")
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
        screenings = scraper.scrape_multiple_dates(num_days=3)  # Reduced to 3 days
        
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
        screenings = api.scrape_next_days(num_days=7)
        
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
    
def main():
    """Main scraper execution"""
    # Setup database
    ensure_database_exists()
    init_db()
    
    session = SessionLocal()
    
    try:
        # Scrape New Beverly
        scrape_new_beverly(session)
        
        # Scrape Laemmle Theatres
        scrape_laemmle(session)
        
        # Scrape American Cinematheque
        scrape_american_cinematheque(session)
        
        # Scrape Landmark Theatres
        scrape_landmark(session)
        
        # Show summary
        show_summary(session)
        
    finally:
        session.close()


if __name__ == "__main__":
    main()