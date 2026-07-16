from pydantic import BaseModel, Field
from typing import Optional, List, Dict
from datetime import datetime
from enum import Enum

class EmotionLabel(str, Enum):
    NEUTRAL = "neutral"
    CALM = "calm"
    EXCITED = "excited"
    SAD = "sad"
    ANGRY = "angry"

class QualityLevel(str, Enum):
    EXCELLENT = "excellent"  # SNR > 20 dB
    USABLE = "usable"        # 10–20 dB
    POOR = "poor"            # < 10 dB

# ============= REQUEST/RESPONSE MODELS =============

class AnnotationCreate(BaseModel):
    speaker: str
    timestamp_start: float
    timestamp_end: float
    text: str
    emotion: EmotionLabel = EmotionLabel.NEUTRAL
    clarity: int = Field(default=3, ge=1, le=5)
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    notes: Optional[str] = None

class DiarizationSegment(BaseModel):
    speaker_id: int
    timestamp_start: float
    timestamp_end: float
    text: Optional[str] = None

class AudioAnalysis(BaseModel):
    file_id: str
    filename: str
    duration_sec: float
    sample_rate: int
    snr_db: float
    quality: QualityLevel
    emotion: EmotionLabel
    emotion_confidence: float
    spectral_centroid_hz: float
    rms_energy: float
    f1_hz: Optional[float] = None
    f2_hz: Optional[float] = None
    transcription: str
    diarization_segments: List[DiarizationSegment] = []
    created_at: datetime = Field(default_factory=datetime.utcnow)

class AnnotationResponse(BaseModel):
    file_id: str
    annotations: List[AnnotationCreate]
    exported_at: datetime = Field(default_factory=datetime.utcnow)

class ExportResponse(BaseModel):
    file_id: str
    format: str  # "json" or "csv"
    data: Dict
    exported_at: datetime = Field(default_factory=datetime.utcnow)

# ============= DATABASE MODELS (SQLAlchemy) =============

from sqlalchemy import Column, String, Float, DateTime, Integer, JSON, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

Base = declarative_base()

class AudioFile(Base):
    __tablename__ = "audio_files"

    id = Column(String, primary_key=True)  # file_id
    filename = Column(String, nullable=False)
    file_path = Column(String, nullable=False)
    duration_sec = Column(Float)
    sample_rate = Column(Integer)
    snr_db = Column(Float)
    quality = Column(String)
    emotion = Column(String)
    emotion_confidence = Column(Float)
    spectral_centroid_hz = Column(Float)
    rms_energy = Column(Float)
    f1_hz = Column(Float, nullable=True)
    f2_hz = Column(Float, nullable=True)
    transcription = Column(String)
    diarization = Column(JSON)  # List[DiarizationSegment] as JSON
    annotations = Column(JSON)  # List[AnnotationCreate] as JSON
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            "file_id": self.id,
            "filename": self.filename,
            "duration_sec": self.duration_sec,
            "snr_db": self.snr_db,
            "quality": self.quality,
            "emotion": self.emotion,
            "transcription": self.transcription,
            "annotations": self.annotations or [],
        }
