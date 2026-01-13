from scrapers.models.base import SessionLocal, init_db
from scrapers.models.theater import Theater
from scrapers.models.movie import Movie
from scrapers.models.screening import Screening

init_db()  # Important!
session = SessionLocal()

movies_without_directors = session.query(Movie).filter(Movie.director == None).all()

print(f"\n{len(movies_without_directors)} movies without directors:")
print("="*60)

for movie in movies_without_directors[:20]:  # Show first 20
    print(f"  • {movie.title}")

session.close()
