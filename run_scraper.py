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
    
    # Show next 10 upcoming screenings
    pacific_tz = pytz.timezone('America/Los_Angeles')
    now = datetime.now(pacific_tz)
    
    upcoming = session.query(Screening).join(Movie).join(Theater)\
        .filter(Screening.screening_datetime >= now)\
        .order_by(Screening.screening_datetime)\
        .limit(10)\
        .all()
    
    if upcoming:
        print("\n📅 Next 10 Upcoming Screenings:")
        for screening in upcoming:
            dt = screening.screening_datetime.strftime("%a %b %d, %I:%M %p")
            print(f"\n{dt} - {screening.movie.title}")
            print(f"   📍 {screening.theater.name}")
            if screening.movie.format:
                print(f"   🎞️  {screening.movie.format}")
            if screening.ticket_url:
                print(f"   🔗 {screening.ticket_url}")


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
    print("🎬 LAEMMLE THEATRES SCRAPER")
    print("="*60)
    
    total_new_screenings = 0
    
    for theater_info in LAEMMLE_THEATERS:
        print(f"\n{'='*60}")
        print(f"📍 {theater_info['name']}")
        print(f"{'='*60}")
        
        # Create/get theater
        theater = get_or_create_theater(
            session,
            name=theater_info['name'],
            address=theater_info['address'],
            city=theater_info['city'],
            state=theater_info['state'],
            website=theater_info['url']
        )
        
        # Scrape schedule (next 7 days)
        scraper = LaemmleScraper(theater_info['url'], theater_info['name'])
        print("\n🔍 Scraping next 7 days...")
        screenings = scraper.scrape_multiple_dates(num_days=7)
        
        # Save to database
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
        
        print(f"✅ Added {new_count} new screenings from {theater_info['name']}")
        total_new_screenings += new_count
    
    print(f"\n{'='*60}")
    print(f"✅ TOTAL: Added {total_new_screenings} new screenings across all Laemmle theaters")
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
        
        # Show summary
        show_summary(session)
        
    finally:
        session.close()


if __name__ == "__main__":
    main()