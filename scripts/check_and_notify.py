"""Check for new screenings and send email notifications to users"""
import sys
from pathlib import Path
import json
from datetime import datetime, timedelta
from collections import defaultdict

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy import text
from scrapers.models.base import SessionLocal, init_db
from scrapers.models.screening import Screening
from scrapers.models.movie import Movie
from scrapers.models.theater import Theater
from scrapers.models.user import User

# File to track last notification time
STATE_FILE = project_root / 'data' / 'notification_state.json'


def load_state():
    """Load the last notification timestamp"""
    if STATE_FILE.exists():
        with open(STATE_FILE) as f:
            state = json.load(f)
            return datetime.fromisoformat(state.get('last_check'))
    return None


def save_state(timestamp):
    """Save the current timestamp as last check time"""
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(STATE_FILE, 'w') as f:
        json.dump({'last_check': timestamp.isoformat()}, f)


def get_new_screenings(session, since):
    """Get screenings added since the given timestamp"""
    query = session.query(Screening).join(Movie).join(Theater)

    if since:
        query = query.filter(Screening.created_at > since)

    return query.all()


def get_users_with_favorites(session):
    """Get all users who have at least one favorite director or theater"""
    users = session.query(User).all()
    result = []

    for user in users:
        # Get favorite directors
        fav_directors = session.execute(text("""
            SELECT director_name FROM favorite_directors
            WHERE user_id = :user_id
        """), {'user_id': user.id}).fetchall()

        # Get favorite theaters
        fav_theaters = session.execute(text("""
            SELECT theater_id FROM favorite_theaters
            WHERE user_id = :user_id
        """), {'user_id': user.id}).fetchall()

        if fav_directors or fav_theaters:
            result.append({
                'user': user,
                'favorite_directors': [d.director_name for d in fav_directors],
                'favorite_theater_ids': [t.theater_id for t in fav_theaters]
            })

    return result


def match_screenings_to_favorites(screenings, user_favorites):
    """Match new screenings to a user's favorites"""
    director_matches = defaultdict(list)
    theater_matches = defaultdict(list)

    for screening in screenings:
        movie = screening.movie
        theater = screening.theater

        # Check director matches
        if movie.director and movie.director in user_favorites['favorite_directors']:
            director_matches[movie.director].append({
                'title': movie.title,
                'theater': theater.name,
                'datetime': screening.screening_datetime.strftime('%A, %B %d at %I:%M %p'),
                'ticket_url': screening.ticket_url
            })

        # Check theater matches
        if theater.id in user_favorites['favorite_theater_ids']:
            theater_matches[theater.name].append({
                'title': movie.title,
                'director': movie.director or 'Unknown',
                'datetime': screening.screening_datetime.strftime('%A, %B %d at %I:%M %p'),
                'ticket_url': screening.ticket_url
            })

    return director_matches, theater_matches


def send_notifications(user_email, director_matches, theater_matches, dry_run=False):
    """Send email notifications to a user"""
    if dry_run:
        if director_matches:
            print(f"  [DRY RUN] Would send director alerts for: {list(director_matches.keys())}")
        if theater_matches:
            print(f"  [DRY RUN] Would send theater alerts for: {list(theater_matches.keys())}")
        return True

    try:
        from scrapers.services.email_service import EmailService
        email_service = EmailService()

        # Send director alerts
        for director, screenings in director_matches.items():
            email_service.send_director_screening_alert(user_email, director, screenings)
            print(f"  Sent director alert for {director} ({len(screenings)} screenings)")

        # Send theater alerts
        for theater_name, screenings in theater_matches.items():
            email_service.send_theater_screening_alert(user_email, theater_name, screenings)
            print(f"  Sent theater alert for {theater_name} ({len(screenings)} screenings)")

        return True

    except ValueError as e:
        print(f"  Email service not configured: {e}")
        return False
    except Exception as e:
        print(f"  Error sending email: {e}")
        return False


def check_and_notify(dry_run=False, force_all=False):
    """Main function to check for new screenings and notify users"""
    init_db()
    session = SessionLocal()

    print("=" * 60)
    print("Checking for new screenings and sending notifications")
    print("=" * 60)

    # Load last check time
    if force_all:
        last_check = None
        print("Force mode: checking ALL screenings")
    else:
        last_check = load_state()
        if last_check:
            print(f"Last check: {last_check}")
        else:
            # First run - only check screenings from the last 24 hours
            last_check = datetime.utcnow() - timedelta(hours=24)
            print(f"First run: checking screenings from last 24 hours")

    # Get new screenings
    new_screenings = get_new_screenings(session, last_check)
    print(f"Found {len(new_screenings)} new screenings")

    if not new_screenings:
        print("No new screenings to notify about")
        save_state(datetime.utcnow())
        session.close()
        return

    # Get users with favorites
    users_with_favorites = get_users_with_favorites(session)
    print(f"Found {len(users_with_favorites)} users with favorites")

    if not users_with_favorites:
        print("No users with favorites to notify")
        save_state(datetime.utcnow())
        session.close()
        return

    # Process each user
    notifications_sent = 0
    for user_data in users_with_favorites:
        user = user_data['user']
        print(f"\nProcessing user: {user.email}")

        # Match screenings to this user's favorites
        director_matches, theater_matches = match_screenings_to_favorites(
            new_screenings, user_data
        )

        if not director_matches and not theater_matches:
            print("  No matching screenings")
            continue

        # Send notifications
        if send_notifications(user.email, director_matches, theater_matches, dry_run):
            notifications_sent += 1

    print(f"\n{'=' * 60}")
    print(f"Notifications sent to {notifications_sent} users")

    # Save state
    if not dry_run:
        save_state(datetime.utcnow())
        print("State saved")

    session.close()


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Check for new screenings and notify users')
    parser.add_argument('--dry-run', action='store_true',
                       help='Print what would be sent without actually sending emails')
    parser.add_argument('--force-all', action='store_true',
                       help='Check all screenings, not just new ones since last check')

    args = parser.parse_args()

    check_and_notify(dry_run=args.dry_run, force_all=args.force_all)
