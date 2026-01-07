-- Theaters table
CREATE TABLE IF NOT EXISTS theaters (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    address TEXT,
    city TEXT,
    state TEXT,
    zip_code TEXT,
    latitude REAL,
    longitude REAL,
    website TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Movies table
CREATE TABLE IF NOT EXISTS movies (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    director TEXT,
    year INTEGER,
    runtime INTEGER,
    format TEXT,  -- e.g., "35mm", "70mm", "Digital"
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(title, director, year)
);

-- Screenings table
CREATE TABLE IF NOT EXISTS screenings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    movie_id INTEGER NOT NULL,
    theater_id INTEGER NOT NULL,
    screening_datetime TIMESTAMP NOT NULL,
    ticket_url TEXT,
    special_notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (movie_id) REFERENCES movies(id),
    FOREIGN KEY (theater_id) REFERENCES theaters(id),
    UNIQUE(movie_id, theater_id, screening_datetime)
);

-- Indexes for faster queries
CREATE INDEX IF NOT EXISTS idx_screenings_datetime ON screenings(screening_datetime);
CREATE INDEX IF NOT EXISTS idx_screenings_theater ON screenings(theater_id);
CREATE INDEX IF NOT EXISTS idx_movies_title ON movies(title);