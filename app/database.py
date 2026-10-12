import os
from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
from app.config import settings

engine = create_engine(
    settings.DATABASE_URL, 
    connect_args={"check_same_thread": False} if "sqlite" in settings.DATABASE_URL else {}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class Comic(Base):
    __tablename__ = "comics"

    id = Column(String(50), primary_key=True, index=True)
    title = Column(String(200), nullable=False)
    prompt = Column(Text, nullable=False)
    character_name = Column(String(100), nullable=False)
    character_appearance = Column(Text, nullable=True)
    setting = Column(String(100), nullable=False)
    tone = Column(String(100), nullable=False)
    art_style = Column(String(100), nullable=False)
    panel_count = Column(Integer, default=5)
    
    # Generation Tracking
    status = Column(String(50), default="pending")  # pending, processing, completed, failed
    current_stage = Column(String(100), default="queued")
    stage_percent = Column(Integer, default=0)
    error_message = Column(Text, nullable=True)
    
    # Honest Fallback & Provider Transparency
    generation_mode = Column(String(50), default="ai_live")  # "ai_live" or "demo_mode"
    story_provider = Column(String(100), default="google-genai")
    image_provider = Column(String(100), default="canvas-illustrator")
    
    pdf_path = Column(String(300), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    panels = relationship("Panel", back_populates="comic", cascade="all, delete-orphan", order_by="Panel.panel_number")

class Panel(Base):
    __tablename__ = "panels"

    id = Column(String(50), primary_key=True, index=True)
    comic_id = Column(String(50), ForeignKey("comics.id"), nullable=False, index=True)
    panel_number = Column(Integer, nullable=False)
    title = Column(String(200), nullable=False)
    scene_description = Column(Text, nullable=True)
    caption = Column(Text, nullable=True)
    narration = Column(Text, nullable=True)
    dialogue = Column(Text, nullable=True)
    image_prompt = Column(Text, nullable=False)
    image_path = Column(String(300), nullable=True)
    is_regenerated = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    comic = relationship("Comic", back_populates="panels")

def init_db():
    Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
