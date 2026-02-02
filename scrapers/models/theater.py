"""Theater model"""
from sqlalchemy import Column, Integer, String, Float
from sqlalchemy.orm import relationship
from .base import Base


class Theater(Base):
    """Theater model"""
    __tablename__ = 'theaters'
    
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False, unique=True)
    address = Column(String)
    city = Column(String)
    state = Column(String)
    zip_code = Column(String)
    latitude = Column(Float)
    longitude = Column(Float)
    website = Column(String)
    description = Column(String)  # Theater introduction/description
    
    # Relationship to screenings
    screenings = relationship("Screening", back_populates="theater")
    
    def __repr__(self):
        return f"<Theater(id={self.id}, name='{self.name}')>"