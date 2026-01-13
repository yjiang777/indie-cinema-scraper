"""Flask web interface for indie cinema scraper"""
from flask import Flask, render_template, request, jsonify
from datetime import datetime, timedelta
import pytz

from scrapers.models.base import SessionLocal
from scrapers.models.theater import Theater
from scrapers.models.movie import Movie
from scrapers.models.screening import Screening

app = Flask(__name__)

# Pacific timezone
pacific_tz = pytz.timezone('America/Los_Angeles')


@app.route('/')
def index():
    """Homepage showing upcoming screenings"""
    session = SessionLocal()
    
    try:
        now = datetime.now(pacific_tz)
        
        # Get theaters for filter dropdown
        theaters = session.query(Theater).order_by(Theater.name).all()
        
        # Get upcoming screenings (next 7 days by default)
        end_date = now + timedelta(days=7)
        
        screenings = session.query(Screening).join(Movie).join(Theater)\
            .filter(Screening.screening_datetime >= now)\
            .filter(Screening.screening_datetime <= end_date)\
            .order_by(Screening.screening_datetime)\
            .limit(50)\
            .all()
        
        # Format for template
        formatted_screenings = []
        for screening in screenings:
            formatted_screenings.append({
                'id': screening.id,
                'movie_title': screening.movie.title,
                'theater_name': screening.theater.name,
                'theater_city': screening.theater.city,
                'datetime': screening.screening_datetime,
                'formatted_date': screening.screening_datetime.strftime('%a, %b %d'),
                'formatted_time': screening.screening_datetime.strftime('%I:%M %p'),
                'format': screening.movie.format or 'Digital',
                'runtime': screening.movie.runtime,
                'ticket_url': screening.ticket_url,
                'special_notes': screening.special_notes
            })
        
        return render_template('index.html', 
                             screenings=formatted_screenings,
                             theaters=theaters)
    
    finally:
        session.close()


@app.route('/search')
def search():
    """Search screenings"""
    session = SessionLocal()
    
    try:
        # Get query parameters
        query = request.args.get('q', '').strip()
        theater_id = request.args.get('theater', '')
        date_filter = request.args.get('date', 'week')  # today, week, month
        format_filter = request.args.get('format', '')
        
        now = datetime.now(pacific_tz)
        
        # Build query
        screenings_query = session.query(Screening).join(Movie).join(Theater)\
            .filter(Screening.screening_datetime >= now)
        
        # Apply filters
        if query:
            screenings_query = screenings_query.filter(
                Movie.title.ilike(f'%{query}%')
            )
        
        if theater_id:
            screenings_query = screenings_query.filter(
                Theater.id == int(theater_id)
            )
        
        if format_filter:
            screenings_query = screenings_query.filter(
                Movie.format == format_filter
            )
        
        # Date filter
        if date_filter == 'today':
            end_date = now.replace(hour=23, minute=59, second=59)
        elif date_filter == 'week':
            end_date = now + timedelta(days=7)
        elif date_filter == 'month':
            end_date = now + timedelta(days=30)
        else:
            end_date = now + timedelta(days=365)
        
        screenings_query = screenings_query.filter(
            Screening.screening_datetime <= end_date
        )
        
        # Execute and format
        screenings = screenings_query.order_by(Screening.screening_datetime).limit(100).all()
        
        formatted_screenings = []
        for screening in screenings:
            formatted_screenings.append({
                'id': screening.id,
                'movie_title': screening.movie.title,
                'theater_name': screening.theater.name,
                'theater_city': screening.theater.city,
                'datetime': screening.screening_datetime.isoformat(),
                'formatted_date': screening.screening_datetime.strftime('%a, %b %d'),
                'formatted_time': screening.screening_datetime.strftime('%I:%M %p'),
                'format': screening.movie.format or 'Digital',
                'runtime': screening.movie.runtime,
                'ticket_url': screening.ticket_url,
                'special_notes': screening.special_notes
            })
        
        return jsonify({
            'success': True,
            'count': len(formatted_screenings),
            'screenings': formatted_screenings
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
    
    finally:
        session.close()


@app.route('/stats')
def stats():
    """Get database stats"""
    session = SessionLocal()
    
    try:
        now = datetime.now(pacific_tz)
        
        theater_count = session.query(Theater).count()
        movie_count = session.query(Movie).count()
        total_screenings = session.query(Screening).count()
        upcoming_screenings = session.query(Screening)\
            .filter(Screening.screening_datetime >= now)\
            .count()
        
        return jsonify({
            'theaters': theater_count,
            'movies': movie_count,
            'total_screenings': total_screenings,
            'upcoming_screenings': upcoming_screenings
        })
    
    finally:
        session.close()


if __name__ == '__main__':
    app.run(debug=True, port=5000)