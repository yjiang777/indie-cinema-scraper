"""Debug New Beverly HTML structure"""
import requests
from bs4 import BeautifulSoup

url = "https://thenewbev.com/schedule/"
print(f"Fetching: {url}\n")

response = requests.get(url)
soup = BeautifulSoup(response.text, 'html.parser')

print("="*60)
print("Looking for program links...")
print("="*60)

# Try different selectors
print("\n1. Links with /program/ in href:")
program_links = soup.find_all('a', href=lambda x: x and '/program/' in x)
print(f"   Found: {len(program_links)} links")

if program_links:
    print("\n   First 3 links:")
    for i, link in enumerate(program_links[:3]):
        print(f"\n   Link {i+1}:")
        print(f"   URL: {link.get('href')}")
        print(f"   Text: {link.get_text()[:100]}")
        print(f"   Classes: {link.get('class')}")
        
        # Show structure
        print(f"   HTML preview:")
        print(f"   {str(link)[:200]}...")

print("\n" + "="*60)
print("Looking for movie titles (h4 tags)...")
print("="*60)

h4_tags = soup.find_all('h4')
print(f"Found {len(h4_tags)} h4 tags")

if h4_tags:
    print("\nFirst 5 movie titles:")
    for i, h4 in enumerate(h4_tags[:5]):
        print(f"   {i+1}. {h4.get_text()}")

print("\n" + "="*60)
print("Looking for date/time patterns...")
print("="*60)

# Look for date patterns
date_elements = soup.find_all(text=lambda x: x and any(month in str(x) for month in ['January', 'February', 'March']))
print(f"Found {len(date_elements)} elements with month names")

if date_elements:
    print("\nFirst 3 date elements:")
    for i, elem in enumerate(date_elements[:3]):
        print(f"   {i+1}. {str(elem).strip()[:100]}")
        # Show parent structure
        if hasattr(elem, 'parent'):
            print(f"      Parent tag: <{elem.parent.name}> class={elem.parent.get('class')}")

print("\n✅ Debug complete!")