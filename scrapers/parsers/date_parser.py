"""Parse dates from various theater websites"""
from datetime import datetime, timedelta
import re
import pytz

def parse_new_beverly_date(date_text, time_text, year=None):
    """
    Parse New Beverly date format
    Examples:
    - "Mon, January 05" + "7:30 pm"
    - "Fri, January 09" + "11:59 pm"
    """
    try:
        # Extract month and day from date_text
        # Format: "Mon, January 05" or "January 05"
        date_pattern = r'(\w+),?\s+(\w+)\s+(\d+)'
        match = re.search(date_pattern, date_text)
        
        if not match:
            return None
        
        # Get month name and day
        parts = match.groups()
        if len(parts) == 3:
            _, month_name, day = parts
        else:
            month_name, day = parts[1], parts[2]
        
        # Use current year if not specified
        if year is None:
            year = datetime.now().year
        
        # Parse time (e.g., "7:30 pm", "11:59 pm")
        time_text = time_text.strip().lower()
        time_pattern = r'(\d+):(\d+)\s*(am|pm)'
        time_match = re.search(time_pattern, time_text)
        
        if not time_match:
            return None
        
        hour, minute, period = time_match.groups()
        hour = int(hour)
        minute = int(minute)
        
        # Convert to 24-hour format
        if period == 'pm' and hour != 12:
            hour += 12
        elif period == 'am' and hour == 12:
            hour = 0
        
        # Create datetime object
        date_str = f"{month_name} {day} {year} {hour}:{minute}"
        dt = datetime.strptime(date_str, "%B %d %Y %H:%M")
        
        # Set to Pacific timezone (LA)
        pacific = pytz.timezone('America/Los_Angeles')
        dt = pacific.localize(dt)
        
        return dt
        
    except Exception as e:
        print(f"Error parsing date '{date_text}' and time '{time_text}': {e}")
        return None

def get_current_year():
    """Get current year, accounting for year transitions"""
    return datetime.now().year