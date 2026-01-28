from sqlalchemy import text, func
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import os
from datetime import datetime, timedelta
import pytz
from dotenv import load_dotenv

# Load environment variables from .env file (for local development)
load_dotenv(override=True)

from scrapers.models.base import SessionLocal, init_db
from scrapers.models.theater import Theater
from scrapers.models.movie import Movie
from scrapers.models.screening import Screening
from scrapers.models.user import User

# Initialize database
init_db()

# Create Flask app FIRST
app = Flask(__name__)

# Set secret key IMMEDIATELY
app.secret_key = os.environ.get('SECRET_KEY')
if not app.secret_key:
    raise ValueError("SECRET_KEY environment variable not set")

# Session settings
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=7)
app.config['SESSION_COOKIE_NAME'] = 'indie_cinema_session'
app.config['SESSION_REFRESH_EACH_REQUEST'] = True

# Production vs development cookie settings
if os.environ.get('RAILWAY_ENVIRONMENT') or os.environ.get('PRODUCTION'):
    app.config['SESSION_COOKIE_SECURE'] = True
    app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
else:
    app.config['SESSION_COOKIE_SAMESITE'] = None
    app.config['SESSION_COOKIE_SECURE'] = False


# THEN initialize Flask-Login and attach to app
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'


@login_manager.user_loader
def load_user(user_id):
    db_session = SessionLocal()
    user = db_session.get(User, int(user_id))  # ← Changed from query().get()
    db_session.close()
    return user

# Add this context processor to make current_user available in templates
@app.context_processor
def inject_user():
    return dict(current_user=current_user)

# Pacific timezone
pacific_tz = pytz.timezone('America/Los_Angeles')


def format_screening_time(dt):
    """Format a screening datetime, treating naive datetimes as Pacific time"""
    if dt.tzinfo is None:
        # Naive datetime - treat as Pacific time
        dt = pacific_tz.localize(dt)
    else:
        # Convert to Pacific if it has timezone
        dt = dt.astimezone(pacific_tz)
    return dt


def get_now_naive():
    """Get current time as naive datetime in Pacific timezone (for DB comparisons)"""
    return datetime.now(pacific_tz).replace(tzinfo=None)


@app.route('/')
def index():
    """Homepage showing upcoming screenings"""
    session = SessionLocal()
    
    try:
        now = get_now_naive()

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
            screen_time = format_screening_time(screening.screening_datetime)
            formatted_screenings.append({
                'id': screening.id,
                'movie_title': screening.movie.title,
                'director': screening.movie.director,
                'theater_name': screening.theater.name,
                'theater_city': screening.theater.city,
                'datetime': screening.screening_datetime,
                'formatted_date': screen_time.strftime('%a, %b %d'),
                'formatted_time': screen_time.strftime('%I:%M %p'),
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
        
        now = get_now_naive()

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
            screen_time = format_screening_time(screening.screening_datetime)
            formatted_screenings.append({
                'id': screening.id,
                'movie_title': screening.movie.title,
                'director': screening.movie.director,
                'theater_name': screening.theater.name,
                'theater_city': screening.theater.city,
                'datetime': screening.screening_datetime.isoformat(),
                'formatted_date': screen_time.strftime('%a, %b %d'),
                'formatted_time': screen_time.strftime('%I:%M %p'),
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
        now = get_now_naive()

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
        now = get_now_naive()

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
        now = get_now_naive()

        screenings = session.query(Screening).join(Movie).join(Theater)\
            .filter(Theater.id == theater_id)\
            .filter(Screening.screening_datetime >= now)\
            .order_by(Screening.screening_datetime)\
            .limit(20)\
            .all()
        
        formatted_screenings = []
        for screening in screenings:
            screen_time = format_screening_time(screening.screening_datetime)
            formatted_screenings.append({
                'id': screening.id,
                'movie_title': screening.movie.title,
                'director': screening.movie.director,
                'formatted_date': screen_time.strftime('%a, %b %d'),
                'formatted_time': screen_time.strftime('%I:%M %p'),
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
    
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    """User signup"""
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        name = request.form.get('name')
        
        db_session = SessionLocal()
        
        # Check if user exists
        existing_user = db_session.query(User).filter_by(email=email).first()
        if existing_user:
            flash('Email already registered', 'error')
            db_session.close()
            return redirect(url_for('signup'))
        
        # Create new user
        password_hash = generate_password_hash(password)
        new_user = User(email=email, password_hash=password_hash, name=name)
        db_session.add(new_user)
        db_session.commit()
        
        # Refresh to get the ID
        db_session.refresh(new_user)
        
        login_user(new_user, remember = True)
        db_session.close()
        
        flash('Account created successfully!', 'success')
        return redirect(url_for('index'))
    
    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    """User login"""
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        session = SessionLocal()
        user = session.query(User).filter_by(email=email).first()
        
        if user and check_password_hash(user.password_hash, password):
            login_user(user, remember = True)
            session.close()
            flash('Logged in successfully!', 'success')
            return redirect(url_for('index'))
        else:
            session.close()
            flash('Invalid email or password', 'error')
            return redirect(url_for('login'))
    
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    """User logout"""
    logout_user()
    flash('Logged out successfully', 'success')
    return redirect(url_for('index'))

@app.route('/dashboard')
@login_required
def dashboard():
    """User dashboard"""
    db_session = SessionLocal()
    
    # Get all theaters for the dropdown
    all_theaters = db_session.query(Theater).order_by(Theater.name).all()
    
    # Get user's favorite theaters
    favorite_theaters = db_session.execute(text("""
        SELECT t.* FROM theaters t
        JOIN favorite_theaters ft ON ft.theater_id = t.id
        WHERE ft.user_id = :user_id
        ORDER BY t.name
    """), {'user_id': current_user.id}).fetchall()
    
    # Get user's favorite directors
    favorite_directors = db_session.execute(text("""
        SELECT * FROM favorite_directors
        WHERE user_id = :user_id
        ORDER BY director_name
    """), {'user_id': current_user.id}).fetchall()
    
    # Get watchlist with movie and theater details
    watchlist_raw = db_session.execute(text("""
        SELECT w.*, s.screening_datetime, m.title, m.director, t.name as theater_name, s.id as screening_id
        FROM watchlist w
        JOIN screenings s ON w.screening_id = s.id
        JOIN movies m ON s.movie_id = m.id
        JOIN theaters t ON s.theater_id = t.id
        WHERE w.user_id = :user_id
        ORDER BY s.screening_datetime
    """), {'user_id': current_user.id}).fetchall()
    
    # Parse datetime strings into datetime objects
    watchlist = []
    for item in watchlist_raw:
        watchlist_item = {
            'screening_id': item.screening_id,
            'title': item.title,
            'director': item.director,
            'theater_name': item.theater_name,
            'screening_datetime': datetime.strptime(item.screening_datetime, '%Y-%m-%d %H:%M:%S.%f')
        }
        watchlist.append(watchlist_item)
    
    db_session.close()
    
    return render_template('dashboard.html', 
                         all_theaters=all_theaters,
                         favorite_theaters=favorite_theaters,
                         favorite_directors=favorite_directors,
                         watchlist=watchlist)

# Favorites API endpoints
# Add favorite theater
@app.route('/api/favorites/theater', methods=['POST'])
@login_required
def add_favorite_theater():
    data = request.get_json()
    theater_id = data.get('theater_id')
    db_session = SessionLocal()
    try:
        db_session.execute(text("""
            INSERT INTO favorite_theaters (user_id, theater_id)
            VALUES (:user_id, :theater_id)
            ON CONFLICT DO NOTHING
        """), {'user_id': current_user.id, 'theater_id': theater_id})
        db_session.commit()
        db_session.close()
        return jsonify({'success': True})
    except Exception as e:
        db_session.close()
        return jsonify({'success': False, 'error': str(e)}), 500

# Remove favorite theater
@app.route('/api/favorites/theater/<int:theater_id>', methods=['DELETE'])
@login_required
def remove_favorite_theater(theater_id):
    db_session = SessionLocal()
    try:
        db_session.execute(text("""
            DELETE FROM favorite_theaters
            WHERE user_id = :user_id AND theater_id = :theater_id
        """), {'user_id': current_user.id, 'theater_id': theater_id})
        db_session.commit()
        db_session.close()
        return jsonify({'success': True})
    except Exception as e:
        db_session.close()
        return jsonify({'success': False, 'error': str(e)}), 500

# Add favorite director
@app.route('/api/favorites/director', methods=['POST'])
@login_required
def add_favorite_director():
    data = request.get_json()
    director_name = data.get('director_name')
    db_session = SessionLocal()
    try:
        db_session.execute(text("""
            INSERT INTO favorite_directors (user_id, director_name)
            VALUES (:user_id, :director_name)
            ON CONFLICT DO NOTHING
        """), {'user_id': current_user.id, 'director_name': director_name})
        db_session.commit()
        db_session.close()
        return jsonify({'success': True})
    except Exception as e:
        db_session.close()
        return jsonify({'success': False, 'error': str(e)}), 500

# Remove favorite director
@app.route('/api/favorites/director/<path:director_name>', methods=['DELETE'])
@login_required
def remove_favorite_director(director_name):
    db_session = SessionLocal()
    try:
        db_session.execute(text("""
            DELETE FROM favorite_directors
            WHERE user_id = :user_id AND director_name = :director_name
        """), {'user_id': current_user.id, 'director_name': director_name})
        db_session.commit()
        db_session.close()
        return jsonify({'success': True})
    except Exception as e:
        db_session.close()
        return jsonify({'success': False, 'error': str(e)}), 500

# Add to watchlist
@app.route('/api/watchlist', methods=['POST'])
@login_required
def add_to_watchlist():
    data = request.get_json()
    screening_id = data.get('screening_id')
    notes = data.get('notes', '')
    db_session = SessionLocal()
    try:
        db_session.execute(text("""
            INSERT INTO watchlist (user_id, screening_id, notes)
            VALUES (:user_id, :screening_id, :notes)
            ON CONFLICT DO NOTHING
        """), {'user_id': current_user.id, 'screening_id': screening_id, 'notes': notes})
        db_session.commit()
        db_session.close()
        return jsonify({'success': True})
    except Exception as e:
        db_session.close()
        return jsonify({'success': False, 'error': str(e)}), 500

# Remove from watchlist
@app.route('/api/watchlist/<int:screening_id>', methods=['DELETE'])
@login_required
def remove_from_watchlist(screening_id):
    db_session = SessionLocal()
    try:
        db_session.execute(text("""
            DELETE FROM watchlist
            WHERE user_id = :user_id AND screening_id = :screening_id
        """), {'user_id': current_user.id, 'screening_id': screening_id})
        db_session.commit()
        db_session.close()
        return jsonify({'success': True})
    except Exception as e:
        db_session.close()
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/directors/list')
def get_directors_list():
    """Get all unique directors"""
    db_session = SessionLocal()
    
    try:
        directors = db_session.execute(text("""
            SELECT DISTINCT director
            FROM movies
            WHERE director IS NOT NULL 
            AND director != ''
            AND director != 'TV Series'
            AND director NOT LIKE 'TV:%'
            ORDER BY director
        """)).fetchall()
        
        directors_list = [d.director for d in directors]
        
        db_session.close()
        return jsonify({'directors': directors_list})
        
    except Exception as e:
        db_session.close()
        return jsonify({'error': str(e)}), 500
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_DEBUG', 'true').lower() == 'true'
    app.run(debug=debug, host='0.0.0.0', port=port)