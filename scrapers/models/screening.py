"""Screening model"""
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, UniqueConstraint, Index
from sqlalchemy.orm import relationship
from datetime import datetime
from .base import Base


class Screening(Base):
    """Screening model"""
    __tablename__ = 'screenings'
    
    id = Column(Integer, primary_key=True)
    movie_id = Column(Integer, ForeignKey('movies.id'), nullable=False)
    theater_id = Column(Integer, ForeignKey('theaters.id'), nullable=False)
    screening_datetime = Column(DateTime, nullable=False, index=True)
    ticket_url = Column(String)
    special_notes = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    
    # Relationships
    movie = relationship("Movie", back_populates="screenings")
    theater = relationship("Theater", back_populates="screenings")
    
    # Unique constraint: same movie at same theater at same time
    __table_args__ = (
        UniqueConstraint('movie_id', 'theater_id', 'screening_datetime',
                        name='uq_screening'),
        Index('idx_screening_datetime', 'screening_datetime'),
        Index('idx_theater_id', 'theater_id'),
        Index('idx_created_at', 'created_at'),
    )
    
    def __repr__(self):
        return f"<Screening(id={self.id}, movie_id={self.movie_id}, theater_id={self.theater_id}, datetime={self.screening_datetime})>"