"""Debug American Cinematheque - Now Showing page"""
import requests
from bs4 import BeautifulSoup
import json

url = "https://www.americancinematheque.com/now-showing/"
print(f"Fetching: {url}\n")

response = requests.get(url, timeout=10)
print(f"Status: {response.status_code}\n")

soup = BeautifulSoup(response.text, 'html.parser')

print("="*60)
print("NOW SHOWING PAGE STRUCTURE")
print("="*60)

# Look for event/screening containers
print("\n🔍 Looking for screening containers...")

selectors = [
    'div.event',
    'div.screening',
    'article.event',
    'div[class*="event"]',
    'div[class*="film"]',
    'div[class*="show"]'
]

for selector in selectors:
    elements = soup.select(selector)
    if elements:
        print(f"\n✅ Found {len(elements)} elements: {selector}")
        if len(elements) > 0:
            print(f"   Classes: {elements[0].get('class')}")
            print(f"   Preview:\n{str(elements[0])[:400]}...\n")
            break

# Look for structured data (JSON-LD)
print("\n" + "="*60)
print("Looking for structured data...")
print("="*60)

json_ld_scripts = soup.find_all('script', type='application/ld+json')
if json_ld_scripts:
    print(f"✅ Found {len(json_ld_scripts)} JSON-LD scripts")
    for i, script in enumerate(json_ld_scripts):
        try:
            data = json.loads(script.string)
            print(f"\nScript {i+1}:")
            print(f"Type: {data.get('@type', 'unknown')}")
            if isinstance(data, list):
                print(f"Array with {len(data)} items")
                if data and '@type' in data[0]:
                    print(f"First item type: {data[0]['@type']}")
            print(json.dumps(data, indent=2)[:500])
            print("...")
        except:
            pass

# Look for calendar/date elements
print("\n" + "="*60)
print("Looking for calendar structure...")
print("="*60)

calendar = soup.find_all(['div', 'section'], class_=lambda x: x and 'calendar' in str(x).lower())
if calendar:
    print(f"✅ Found {len(calendar)} calendar elements")
    for cal in calendar[:2]:
        print(f"\nClasses: {cal.get('class')}")
        print(f"Preview: {str(cal)[:300]}...")

# Look for theater filter/selector
print("\n" + "="*60)
print("Looking for theater filters...")
print("="*60)

filters = soup.find_all(['select', 'button', 'a'], 
                        string=lambda x: x and any(t in str(x).lower() 
                        for t in ['aero', 'egyptian', 'los feliz', 'theater', 'venue']))

if filters:
    print(f"✅ Found {len(filters)} theater-related elements:")
    for f in filters[:5]:
        print(f"   • {f.name}: {f.get_text().strip()[:50]} (class={f.get('class')})")

# Check if content is loaded via JS
print("\n" + "="*60)
print("Checking for dynamic content indicators...")
print("="*60)

# Look for React/Vue mounting points
react_root = soup.find(id='root') or soup.find(id='app') or soup.find(class_='app')
if react_root:
    print("⚠️  Found React/Vue root - content likely loaded via JS")
    print(f"   Element: <{react_root.name}> id={react_root.get('id')} class={react_root.get('class')}")

# Check page text length (short = JS-rendered)
text_content = soup.get_text()
print(f"\nPage text length: {len(text_content)} chars")
if len(text_content) < 5000:
    print("⚠️  Very little content - likely JS-rendered")
else:
    print("✅ Substantial content present")

print("\n✅ Debug complete!")