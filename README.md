# Indie Cinema Scraper

A web scraper that aggregates indie movie theater showtimes in Los Angeles, designed for film enthusiasts who want to discover repertory screenings, special formats (35mm, 70mm), and director-based film discovery.

## 🎯 Project Goals

- **Aggregate showtimes** from indie/arthouse theaters across LA
- **Geographic filtering** by distance from user location
- **Format filtering** (35mm, 70mm, IB Technicolor, Digital)
- **Director-based discovery** - Get notified when Stanley Kubrick films screen
- **Centralized database** - No more checking 10+ different theater websites

## ✅ Current Status

**Phase 1: Core Infrastructure & Initial Scrapers** (Complete)

### Theaters Implemented (9 locations)
- ✅ **New Beverly Cinema** (1 location) - Static HTML scraper
- ✅ **Laemmle Theatres** (8 locations) - Date-based scraper
  - Royal (LA)
  - Town Center 5 (Encino)
  - Glendale
  - Monica Film Center (Santa Monica)
  - Newhall (Santa Clarita)
  - NoHo 7 (North Hollywood)
  - Claremont 5
  - Playhouse 7 (Pasadena)

### Database Stats (as of last run)
- 🎭 9 Theaters
- 🎬 65+ Unique Movies
- 🎫 486+ Screenings

## 🏗️ Project Structure
```
indie-cinema-scraper/
├── README.md
├── requirements.txt
├── run_scraper.py              # Main execution script
├── database/
│   ├── schema.sql              # SQLite schema definition
│   └── indie_cinema.db         # Database (created on first run)
├── scrapers/
│   ├── models/
│   │   ├── base.py             # SQLAlchemy engine & session
│   │   ├── theater.py          # Theater model
│   │   ├── movie.py            # Movie model
│   │   └── screening.py        # Screening model (with relationships)
│   ├── parsers/
│   │   ├── date_parser.py      # Date/time parsing utilities
│   │   └── movie_normalizer.py # Title cleaning, format extraction
│   ├── new_beverly/
│   │   └── scraper.py          # NewBeverlyScraper class
│   └── laemmle/
│       ├── theaters.py         # Theater location data
│       └── scraper.py          # LaemmleScraper class
└── debug_*.py                  # Debug/testing scripts
```

## 🚀 Setup & Installation

### Prerequisites
- Python 3.11+ (ARM64 on Apple Silicon recommended)
- Virtual environment support

### Installation Steps

1. **Clone the repository**
```bash
cd indie-cinema-scraper
```

2. **Create virtual environment**
```bash
# On macOS (Apple Silicon)
/opt/homebrew/bin/python3.11 -m venv venv

# On macOS (Intel) or Linux
python3 -m venv venv
```

3. **Activate virtual environment**
```bash
source venv/bin/activate  # macOS/Linux
```

4. **Install dependencies**
```bash
pip install -r requirements.txt
```

5. **Verify setup**
```bash
python -c "import platform; print(platform.machine())"
# Should show: arm64 (Apple Silicon) or x86_64 (Intel)
```

## 📊 Database Schema

**SQLite database** with 3 main tables:

### Tables
- **theaters** - Theater locations, addresses, coordinates
- **movies** - Movie titles, directors, runtime, format
- **screenings** - Showtimes linking movies to theaters

### Key Features
- Unique constraints prevent duplicate screenings
- Foreign key relationships for data integrity
- Indexes on datetime and theater_id for fast queries
- SQLAlchemy ORM for easy querying

## 🎬 Running the Scrapers

### Basic Usage
```bash
python run_scraper.py
```

This will:
1. Initialize database (if needed)
2. Scrape New Beverly Cinema
3. Scrape all 8 Laemmle locations
4. Display summary of scraped data
5. Show next 10 upcoming screenings

### Output Example
```
============================================================
🎬 NEW BEVERLY CINEMA SCRAPER
============================================================
✅ Created theater: New Beverly Cinema
🔍 Scraping schedule...
Extracted 70 screenings

============================================================
🎬 LAEMMLE THEATRES SCRAPER
============================================================
📍 Laemmle Royal
✅ Added 36 new screenings from Laemmle Royal
...

============================================================
📊 DATABASE SUMMARY
============================================================
🎭 Theaters: 9
🎬 Movies: 65
🎫 Screenings: 486

📅 Next 10 Upcoming Screenings:
Wed Jan 07, 07:30 PM - The Choral
   📍 Laemmle Royal
   🎞️  Digital
   🔗 https://www.laemmle.com/film/choral
```

### Re-running the Scraper
The scraper is **idempotent** - running it multiple times won't create duplicates. Existing screenings are skipped, new ones are added.

## 🔧 Technical Details

### Scraping Strategies

**New Beverly Cinema**
- **Method:** Static HTML parsing with BeautifulSoup
- **URL:** https://thenewbev.com/schedule/
- **Challenges:** Date/time spread across text nodes, double features
- **Solution:** Custom parser that handles split times and titles

**Laemmle Theatres**
- **Method:** Date-parameterized requests (`?date=2026-01-07`)
- **URL Pattern:** https://www.laemmle.com/theater/{theater-name}
- **Challenges:** Past vs future showtimes, multi-theater coordination
- **Solution:** 7-day rolling scrape, class-based filtering

### Data Normalization
- **Title cleaning:** Remove format indicators like "(35mm)", "in 70mm"
- **Format extraction:** Parse text for 35mm, 70mm, IB Technicolor
- **Timezone handling:** All datetimes in Pacific timezone (pytz)
- **Deduplication:** Unique constraint on (movie, theater, datetime)

### Dependencies
```
requests==2.31.0          # HTTP requests
beautifulsoup4==4.12.2    # HTML parsing
lxml==5.1.0               # XML/HTML parser
python-dateutil==2.8.2    # Date parsing
pytz==2024.1              # Timezone support
sqlalchemy==2.0.23        # ORM and database
python-dotenv==1.0.0      # Environment variables
```

## 📝 TODO / Roadmap

### Phase 2: Complete Theater Coverage (Remaining)
- [ ] **American Cinematheque** (3 locations)
  - Aero Theatre (Santa Monica)
  - Egyptian Theatre (Hollywood)
  - Los Feliz 3
  - Challenge: JavaScript-heavy site, may need Playwright or API
  
- [ ] **Landmark Theatres** (3 LA locations)
  - Nuart Theatre (West LA)
  - Westwood (Westwood)
  - Sunset (West Hollywood)
  - Challenge: Webedia platform, JS-rendered content

### Phase 3: Enhanced Metadata
- [ ] Integrate TMDB API for director information
- [ ] Add movie posters, genres, plot summaries
- [ ] Extract cast information
- [ ] Add user ratings/reviews

### Phase 4: Query Interface
- [ ] CLI query tool
  - `python query.py --director "Stanley Kubrick"`
  - `python query.py --format 35mm --tonight`
  - `python query.py --theater "New Beverly" --next-week`
- [ ] Web interface (Flask/FastAPI)
  - Search by movie, director, theater
  - Filter by date range, format
  - Map view with distance filtering
- [ ] Notification system
  - Email alerts for followed directors
  - SMS for nearby screenings

### Phase 5: Production Features
- [ ] Automated daily scraping (cron/systemd)
- [ ] Error handling and retry logic
- [ ] Logging and monitoring
- [ ] Database backups
- [ ] API endpoint for external access
- [ ] Geolocation-based distance filtering

### Phase 6: User Interface
- [ ] React web app
- [ ] User accounts and preferences
- [ ] "Follow" directors feature
- [ ] Calendar integration
- [ ] Mobile app (React Native)

## 🐛 Known Issues

1. **Playwright installation fails on Apple Silicon**
   - Status: Deferred to Phase 2
   - Workaround: Focus on static HTML sites first

2. **Laemmle Playhouse 7 returns 0 screenings**
   - Possible causes: Theater temporarily closed, different HTML structure
   - Action: Needs investigation

3. **No ticket purchase links for Laemmle**
   - Current: Links to film page, not direct ticket purchase
   - Future: May need to investigate ticketing platform API

## 🔍 Development Notes

### Environment Setup (Apple Silicon)
Key lessons learned:
- Use native ARM Python (`/opt/homebrew/bin/python3.11`)
- Avoid x86 Python running under Rosetta
- Disable Conda auto-activation if it causes conflicts
- Verify architecture with `platform.machine()` → should be `arm64`

### Debugging Tools
Created several debug scripts for investigating HTML structure:
- `debug_new_beverly.py` - Inspect New Beverly HTML
- `debug_laemmle.py` - Inspect Laemmle structure
- `test_scraping.py` - Basic connectivity tests
- `verify_setup.py` - Environment verification

## 📄 License

MIT License (or specify your chosen license)

## 🙏 Acknowledgments

- Theater websites for providing public schedule information
- BeautifulSoup for excellent HTML parsing
- SQLAlchemy for robust ORM functionality

---

**Built with ❤️ for indie cinema enthusiasts in Los Angeles**