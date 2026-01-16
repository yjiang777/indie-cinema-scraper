import sys
from pathlib import Path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from scrapers.models.base import SessionLocal, init_db
from scrapers.models.theater import Theater
from scrapers.models.movie import Movie  # ← Add these
from scrapers.models.screening import Screening  # ← Add these

init_db()
session = SessionLocal()

theaters = session.query(Theater).order_by(Theater.name).all()

print(f"Checking coordinates for {len(theaters)} theaters:")
print("="*60)

missing = []
for theater in theaters:
    if theater.latitude and theater.longitude:
        print(f"✅ {theater.name}: ({theater.latitude}, {theater.longitude})")
    else:
        print(f"❌ {theater.name}: Missing coordinates")
        missing.append(theater)

print(f"\n{len(missing)} theaters need geocoding")

session.close()