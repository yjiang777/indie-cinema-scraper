"""User model for authentication"""
from sqlalchemy import Column, Integer, String, DateTime
from datetime import datetime
from flask_login import UserMixin
from .base import Base

class User(UserMixin, Base):
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True)
    email = Column(String, unique=True, nullable=False)
    password_hash = Column(String, nullable=False)
    name = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f"<User(email='{self.email}')>"