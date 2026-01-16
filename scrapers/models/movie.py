from sqlalchemy import Column, Integer, String, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
from .base import Base

class Movie(Base):
    __tablename__ = 'movies'
    
    id = Column(Integer, primary_key=True)
    title = Column(String, nullable=False)
    director = Column(String)
    year = Column(Integer)  # ← Add this line
    runtime = Column(Integer)
    format = Column(String)
    tmdb_id = Column(Integer)
    poster_url = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    screenings = relationship("Screening", back_populates="movie")
    
    def __repr__(self):
        return f"<Movie(title='{self.title}', director='{self.director}')>"