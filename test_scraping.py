"""Test basic web scraping"""
import requests
from bs4 import BeautifulSoup

url = "https://thenewbev.com/schedule/"
print(f"Testing: {url}")

response = requests.get(url)
print(f"Status: {response.status_code}")

soup = BeautifulSoup(response.text, 'html.parser')
movies = soup.find_all('h4')
print(f"Found {len(movies)} movie headings")
print("\nFirst 3 movies:")
for movie in movies[:3]:
    print(f"  - {movie.get_text()}")
    
print("\n✅ Basic scraping works! Ready to build.")
