"""Investigate revivalhouses.com structure"""
import requests
from bs4 import BeautifulSoup
import json

url = "https://www.revivalhouses.com/"
print(f"Fetching: {url}\n")

response = requests.get(url, timeout=10)
print(f"Status: {response.status_code}\n")

soup = BeautifulSoup(response.text, 'html.parser')

print("="*60)
print("SITE STRUCTURE")
print("="*60)

# Check for API endpoints in scripts
print("\n🔍 Looking for API endpoints...")
scripts = soup.find_all('script')

for script in scripts:
    if script.string:
        text = script.string
        # Look for API URLs
        if 'api' in text.lower() or 'endpoint' in text.lower() or '/v1/' in text:
            print(f"\n✅ Found potential API reference:")
            print(text[:500])
            print("...")

# Look for data in script tags (Next.js often uses __NEXT_DATA__)
print("\n" + "="*60)
print("Looking for embedded data...")
print("="*60)

next_data = soup.find('script', id='__NEXT_DATA__')
if next_data:
    print("✅ Found __NEXT_DATA__ (Next.js site)")
    try:
        data = json.loads(next_data.string)
        print(f"\nData structure preview:")
        print(json.dumps(data, indent=2)[:1000])
        print("...")
    except:
        print("Could not parse JSON")

# Check for theater/screening links
print("\n" + "="*60)
print("Looking for theater/screening structure...")
print("="*60)

links = soup.find_all('a', href=True)
theater_links = []
screening_links = []

for link in links:
    href = link.get('href', '')
    text = link.get_text().strip()
    
    if '/theater/' in href or '/venue/' in href:
        theater_links.append((text, href))
    elif '/film/' in href or '/screening/' in href or '/event/' in href:
        screening_links.append((text, href))

if theater_links:
    print(f"\n✅ Found {len(theater_links)} theater links:")
    for text, href in theater_links[:10]:
        print(f"   • {text} → {href}")

if screening_links:
    print(f"\n✅ Found {len(screening_links)} screening links:")
    for text, href in screening_links[:10]:
        print(f"   • {text[:50]} → {href}")

# Check for filters/search
print("\n" + "="*60)
print("Looking for filters/search capabilities...")
print("="*60)

filters = soup.find_all(['select', 'input'], attrs={'name': True})
if filters:
    print(f"Found {len(filters)} filter elements:")
    for f in filters:
        print(f"   • {f.name}: name='{f.get('name')}' type='{f.get('type')}'")

# Check robots.txt and sitemap
print("\n" + "="*60)
print("Checking robots.txt...")
print("="*60)

try:
    robots = requests.get("https://www.revivalhouses.com/robots.txt", timeout=5)
    if robots.status_code == 200:
        print(robots.text[:500])
except:
    print("No robots.txt found")

print("\n✅ Debug complete!")