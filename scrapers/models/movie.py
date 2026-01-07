"""Movie model"""
from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship
from .base import Base


class Movie(Base):
    """Movie model"""
    __tablename__ = 'movies'
    
    id = Column(Integer, primary_key=True)
    title = Column(String, nullable=False, unique=True, index=True)
    director = Column(String)
    year = Column(Integer)
    runtime = Column(Integer)
    format = Column(String)
    
    # Relationship to screenings
    screenings = relationship("Screening", back_populates="movie")
    
    def __repr__(self):
        return f"<Movie(id={self.id}, title='{self.title}')>"