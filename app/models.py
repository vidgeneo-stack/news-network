from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from .database import Base

class SourceType(str, enum.Enum):
    RSS = "rss"
    TELEGRAM = "telegram"
    VK = "vk"

class City(Base):
    __tablename__ = "cities"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    country = Column(String(100), default="Россия")
    
    sources = relationship("Source", back_populates="city")
    news = relationship("News", back_populates="city")

class Source(Base):
    __tablename__ = "sources"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    url = Column(String(500), nullable=False, unique=True)
    source_type = Column(Enum(SourceType), default=SourceType.RSS)
    city_id = Column(Integer, ForeignKey("cities.id"))
    
    city = relationship("City", back_populates="sources")
    news = relationship("News", back_populates="source")

class News(Base):
    __tablename__ = "news"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(500), nullable=False)
    content = Column(Text)
    source_url = Column(String(500))
    image_url = Column(String(500))
    video_url = Column(String(500))
    published_at = Column(DateTime(timezone=True), server_default=func.now())
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    status = Column(String(50), default="draft")  # draft, published, archived
    city_id = Column(Integer, ForeignKey("cities.id"))
    source_id = Column(Integer, ForeignKey("sources.id"))
    
    city = relationship("City", back_populates="news")
    source = relationship("Source", back_populates="news")
