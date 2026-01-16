"""Flask web interface for indie cinema scraper"""
from flask import Flask, render_template, request, jsonify
from datetime import datetime, timedelta
import pytz
from sqlalchemy import func

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
        now_naive = now.replace(tzinfo=None)
        
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
                'director': screening.movie.director,
                'theater_name': screening.theater.name,
                'theater_city': screening.theater.city,
                'datetime': screening.screening_datetime,
                'formatted_date': screening.screening_datetime.strftime('%a, %b %d'),
                'formatted_time': screening.screening_datetime.strftime('%I:%M %p'),
                'format': screening.movie.format or 'Digital',
                'poster_url': screening.movie.poster_url,
                'runtime': screening.movie.runtime,
                'ticket_url': screening.ticket_url,
                'special_notes': screening.special_notes
            })
        
        return render_template('index.html', 
                             screenings=formatted_screenings,
                             theaters=theaters)
    
    finally:
        session.close()

@app.route('/map')
def map_view():
    """Map view of theaters"""
    return render_template('map.html')


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
        now_naive = now.replace(tzinfo=None)
        
        # Build query
        screenings_query = session.query(Screening).join(Movie).join(Theater)\
            .filter(Screening.screening_datetime >= now)
        
        # Apply filters
        if query:
            screenings_query = screenings_query.filter(
                (Movie.title.ilike(f'%{query}%')) |
                (Movie.director.ilike(f'%{query}%'))
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
                'director': screening.movie.director,
                'theater_name': screening.theater.name,
                'theater_city': screening.theater.city,
                'datetime': screening.screening_datetime.isoformat(),
                'formatted_date': screening.screening_datetime.strftime('%a, %b %d'),
                'formatted_time': screening.screening_datetime.strftime('%I:%M %p'),
                'format': screening.movie.format or 'Digital',
                'poster_url': screening.movie.poster_url,
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


@app.route('/directors')
def directors():
    """Get list of all directors with upcoming screenings"""
    session = SessionLocal()
    
    try:
        now = datetime.now(pacific_tz)
        now_naive = now.replace(tzinfo=None)
        
        # Get unique directors with screening counts
        directors_query = session.query(
            Movie.director,
            func.count(Screening.id).label('screening_count')
        ).join(Screening).join(Theater)\
         .filter(Movie.director.isnot(None))\
         .filter(Screening.screening_datetime >= now)\
         .group_by(Movie.director)\
         .order_by(func.count(Screening.id).desc())\
         .all()
        
        directors_list = [
            {
                'name': director,
                'screening_count': count
            }
            for director, count in directors_query
        ]
        
        return jsonify({
            'success': True,
            'directors': directors_list
        })
    
    finally:
        session.close()


@app.route('/stats')
def stats():
    """Get database stats"""
    session = SessionLocal()
    
    try:
        now = datetime.now(pacific_tz)
        now_naive = now.replace(tzinfo=None)

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
@app.route('/api/theaters')
def api_theaters():
    """Get all theaters with coordinates and optional distance filtering"""
    session = SessionLocal()
    
    try:
        # Get user location from query params
        user_lat = request.args.get('lat', type=float)
        user_lon = request.args.get('lon', type=float)
        max_distance = request.args.get('max_distance', type=float)
        
        theaters = session.query(Theater).all()
        
        theater_list = []
        for theater in theaters:
            # Calculate distance if user location provided
            distance = None
            if user_lat and user_lon and theater.latitude and theater.longitude:
                distance = calculate_distance(
                    user_lat, user_lon,
                    theater.latitude, theater.longitude
                )
            
            # Filter by max distance if specified
            if max_distance and distance and distance > max_distance:
                continue
            
            theater_list.append({
                'id': theater.id,
                'name': theater.name,
                'address': theater.address,
                'city': theater.city,
                'latitude': theater.latitude,
                'longitude': theater.longitude,
                'website': theater.website,
                'distance': round(distance, 1) if distance else None
            })
        
        # Sort by distance if available
        if user_lat and user_lon:
            theater_list.sort(key=lambda x: x['distance'] if x['distance'] else float('inf'))
        
        return jsonify({
            'success': True,
            'theaters': theater_list
        })
    
    finally:
        session.close()


@app.route('/api/theaters/<int:theater_id>/screenings')
def api_theater_screenings(theater_id):
    """Get upcoming screenings for a specific theater"""
    session = SessionLocal()
    
    try:
        now = datetime.now(pacific_tz)
        now_naive = now.replace(tzinfo=None)
        
        screenings = session.query(Screening).join(Movie).join(Theater)\
            .filter(Theater.id == theater_id)\
            .filter(Screening.screening_datetime >= now)\
            .order_by(Screening.screening_datetime)\
            .limit(20)\
            .all()
        
        formatted_screenings = []
        for screening in screenings:
            formatted_screenings.append({
                'id': screening.id,
                'movie_title': screening.movie.title,
                'director': screening.movie.director,
                'formatted_date': screening.screening_datetime.strftime('%a, %b %d'),
                'formatted_time': screening.screening_datetime.strftime('%I:%M %p'),
                'format': screening.movie.format or 'Digital',
                'poster_url': screening.movie.poster_url,
                'ticket_url': screening.ticket_url
            })
        
        return jsonify({
            'success': True,
            'screenings': formatted_screenings
        })
    
    finally:
        session.close()


def calculate_distance(lat1, lon1, lat2, lon2):
    """
    Calculate distance between two points using Haversine formula
    Returns distance in miles
    """
    from math import radians, cos, sin, asin, sqrt
    
    # Convert to radians
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    
    # Haversine formula
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * asin(sqrt(a))
    
    # Radius of earth in miles
    r = 3956
    
    return c * r

if __name__ == '__main__':
    app.run(debug=True, port=5000)