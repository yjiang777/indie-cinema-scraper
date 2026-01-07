"""Debug Landmark Theatres structure"""
import requests
from bs4 import BeautifulSoup
import json

# Test with Nuart Theatre
url = "https://www.landmarktheatres.com/los-angeles/nuart-theatre"
print(f"Fetching: {url}\n")

try:
    response = requests.get(url, timeout=10)
    print(f"Status: {response.status_code}\n")
except Exception as e:
    print(f"Error: {e}\n")
    exit()

soup = BeautifulSoup(response.text, 'html.parser')

print("="*60)
print("PAGE STRUCTURE")
print("="*60)

# Check for theater name
theater_name = soup.find('h1')
print(f"\nTheater name: {theater_name.get_text().strip() if theater_name else 'Not found'}")

# Check page content length
text_content = soup.get_text()
print(f"Page text length: {len(text_content)} chars")

if len(text_content) < 5000:
    print("⚠️  Very little content - likely JS-rendered")

# Look for screening containers
print("\n" + "="*60)
print("Looking for screening containers...")
print("="*60)

selectors = [
    'div.film',
    'div.movie',
    'div.showtime',
    'div[class*="film"]',
    'div[class*="movie"]',
    'article'
]

for selector in selectors:
    elements = soup.select(selector)
    if elements:
        print(f"\n✅ Found {len(elements)} elements: {selector}")
        if elements:
            print(f"   Classes: {elements[0].get('class')}")
            print(f"   Preview: {str(elements[0])[:300]}...")

# Look for JSON-LD structured data
print("\n" + "="*60)
print("Looking for structured data (JSON-LD)...")
print("="*60)

json_ld_scripts = soup.find_all('script', type='application/ld+json')
if json_ld_scripts:
    print(f"✅ Found {len(json_ld_scripts)} JSON-LD scripts")
    for i, script in enumerate(json_ld_scripts):
        try:
            data = json.loads(script.string)
            print(f"\nScript {i+1}:")
            print(f"Type: {data.get('@type', 'unknown')}")
            print(json.dumps(data, indent=2)[:500])
            print("...")
        except:
            pass

# Look for React/Vue mounting points
print("\n" + "="*60)
print("Checking for dynamic content indicators...")
print("="*60)

react_root = soup.find(id='root') or soup.find(id='app') or soup.find(class_='app')
if react_root:
    print("⚠️  Found React/Vue root - content loaded via JS")
    print(f"   Element: <{react_root.name}> id={react_root.get('id')} class={react_root.get('class')}")

# Check for embedded calendar/widget
print("\n" + "="*60)
print("Looking for iframes or embedded content...")
print("="*60)

iframes = soup.find_all('iframe')
if iframes:
    print(f"Found {len(iframes)} iframes:")
    for iframe in iframes:
        src = iframe.get('src', '')
        print(f"   • {src}")

# Check for API-like scripts
print("\n" + "="*60)
print("Looking for API endpoints in scripts...")
print("="*60)

scripts = soup.find_all('script', src=False)
found_api = False

for script in scripts:
    if script.string:
        text = script.string
        if 'api' in text.lower() or 'endpoint' in text.lower() or '/v1/' in text or 'graphql' in text.lower():
            print("\n✅ Found potential API reference:")
            print(text[:500])
            print("...")
            found_api = True
            break

if not found_api:
    print("No obvious API endpoints found in scripts")

print("\n✅ Debug complete!")
