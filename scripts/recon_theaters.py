"""Quick reconnaissance of potential theater sites"""
import requests
from bs4 import BeautifulSoup

theaters = [
    ("UCLA Film & Television Archive", "https://cinema.ucla.edu"),
    ("USC Cinema", "https://cinema.usc.edu/events/index.cfm"),
    ("Cinepolis Inglewood", "https://www.cinepolisusa.com/inglewood/home"),
    ("Alamo Drafthouse LA", "https://drafthouse.com/los-angeles")
]

print("="*60)
print("THEATER RECONNAISSANCE")
print("="*60)

for name, url in theaters:
    print(f"\n{'='*60}")
    print(f"🎬 {name}")
    print(f"🔗 {url}")
    print(f"{'='*60}")
    
    try:
        response = requests.get(url, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Check page size
        text_length = len(soup.get_text())
        print(f"Page size: {text_length} chars", end='')
        
        if text_length < 5000:
            print(" ⚠️ (likely JS-rendered)")
        else:
            print(" ✅ (substantial content)")
        
        # Check for common platforms
        page_text = response.text.lower()
        
        platforms = {
            'eventive': 'eventive' in page_text,
            'showingtime': 'showingtime' in page_text or 'sho.com' in page_text,
            'vista': 'vista' in page_text or 'veezi' in page_text,
            'eventbrite': 'eventbrite' in page_text,
            'ticketing': 'ticketing' in page_text,
            'algolia': 'algolia' in page_text,
            'wordpress': 'wp-content' in page_text or 'wordpress' in page_text
        }
        
        detected = [name for name, found in platforms.items() if found]
        
        if detected:
            print(f"Platform hints: {', '.join(detected)}")
        else:
            print("Platform: Unknown (needs deeper inspection)")
        
        # Check for schedule/calendar links
        links = soup.find_all('a', href=True)
        schedule_links = []
        
        for link in links:
            text = link.get_text().strip().lower()
            href = link.get('href', '').lower()
            
            if any(word in text or word in href for word in ['schedule', 'calendar', 'showtimes', 'now showing', 'upcoming']):
                schedule_links.append((link.get_text().strip()[:50], link.get('href')))
        
        if schedule_links:
            print(f"\nSchedule links found: {len(schedule_links)}")
            for text, href in schedule_links[:3]:
                print(f"   • {text} → {href[:60]}")
        
        # Check for React/Vue
        if soup.find(id='root') or soup.find(id='app'):
            print("⚠️  React/Vue detected (JS-heavy)")
        
        # Look for API calls in scripts
        scripts = soup.find_all('script')
        api_found = False
        
        for script in scripts:
            if script.string and ('api' in script.string.lower() or 'endpoint' in script.string.lower()):
                api_found = True
                break
        
        if api_found:
            print("✅ Potential API detected")
        
    except Exception as e:
        print(f"❌ Error: {e}")

print("\n" + "="*60)
print("RECONNAISSANCE COMPLETE")
print("="*60)