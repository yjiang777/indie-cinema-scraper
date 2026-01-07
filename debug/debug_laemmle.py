"""Debug Laemmle - Date info and future showtimes"""
import requests
from bs4 import BeautifulSoup

theater_url = "https://www.laemmle.com/theater/royal"
print(f"Fetching: {theater_url}\n")

response = requests.get(theater_url)
soup = BeautifulSoup(response.text, 'html.parser')

print("="*60)
print("DATE INFORMATION")
print("="*60)

# Look for date selector or date display
date_elements = soup.find_all(string=lambda x: x and any(month in str(x).lower() for month in ['january', 'february', 'march', 'april', 'may', 'june', 'july', 'august', 'september', 'october', 'november', 'december']))

if date_elements:
    print("\nFound date references:")
    for elem in date_elements[:5]:
        print(f"   • {elem.strip()}")
        print(f"     Parent: <{elem.parent.name}> class={elem.parent.get('class')}")

# Look for date picker/selector
date_picker = soup.select('select[name*="date"], input[type="date"], div[class*="date"]')
if date_picker:
    print(f"\n✅ Found {len(date_picker)} date selector(s)")
    for picker in date_picker:
        print(f"   {picker}")

print("\n" + "="*60)
print("SHOWTIME CLASSES (Past vs Future)")
print("="*60)

# Get all showtime divs
all_showtimes = soup.select('div.showtime')
print(f"\nTotal showtimes found: {len(all_showtimes)}")

# Group by class patterns
class_patterns = {}
for showtime in all_showtimes:
    classes = ' '.join(showtime.get('class', []))
    if classes not in class_patterns:
        class_patterns[classes] = []
    class_patterns[classes].append(showtime.get_text().strip())

print("\nShowtime types found:")
for pattern, times in class_patterns.items():
    print(f"\n   Class: '{pattern}'")
    print(f"   Count: {len(times)}")
    print(f"   Examples: {times[:3]}")

print("\n" + "="*60)
print("CHECKING FOR TICKET LINKS")
print("="*60)

# Look for active showtimes with links
active_showtimes = soup.select('a.showtime')
if active_showtimes:
    print(f"\n✅ Found {len(active_showtimes)} clickable showtimes (probably future)")
    for i, showtime in enumerate(active_showtimes[:5]):
        time_text = showtime.get_text().strip()
        href = showtime.get('href')
        classes = ' '.join(showtime.get('class', []))
        print(f"\n   {i+1}. {time_text}")
        print(f"      Classes: {classes}")
        print(f"      Link: {href}")
else:
    print("\n❌ No clickable showtimes found (all may be past)")

print("\n" + "="*60)
print("PAGE TITLE / HEADER")
print("="*60)

# Check page title for date
title = soup.find('title')
if title:
    print(f"\nPage title: {title.get_text()}")

# Check for h1/h2 headers
headers = soup.find_all(['h1', 'h2', 'h3'])
print(f"\nHeaders on page:")
for header in headers[:10]:
    text = header.get_text().strip()
    if text:
        print(f"   {header.name}: {text}")

print("\n✅ Debug complete!")