from pathlib import Path
from enum import Enum
import os

class AudioFormat(str, Enum):
    WAV = "wav"
    MP3 = "mp3"
    FLAC = "flac"

BASE_DIR = Path(__file__).parent
UPLOAD_DIR = BASE_DIR / "uploads"
ANNOTATIONS_DIR = BASE_DIR / "annotations"
DB_PATH = BASE_DIR / "neurosonix.db"
METADATA_FILE = BASE_DIR / "metadata.json"

# Create dirs if missing
UPLOAD_DIR.mkdir(exist_ok=True)
ANNOTATIONS_DIR.mkdir(exist_ok=True)

# Audio processing settings
SAMPLE_RATE = 16000
CHUNK_DURATION_SEC = 0.5  # For SNR calculation
MIN_DURATION_SEC = 0.5
MAX_DURATION_SEC = 300  # 5 minutes max

# Whisper settings
WHISPER_MODEL = "base"  # Can swap to "small", "medium" for better accuracy
WHISPER_DEVICE = "cpu"  # Use "cuda" if GPU available

# SNR thresholds (quality traffic light)
SNR_EXCELLENT = 20  # dB (green)
SNR_USABLE = 10     # dB (yellow)
# Below 10 dB = red (poor)

# Diarization settings
MAX_SPEAKERS = 4
SPEAKER_COLORS = ["#FF6B6B", "#4ECDC4", "#45B7D1", "#FFA07A"]

# API settings
CORS_ORIGINS = [
    "http://localhost:5173",  # Vite default
    "http://localhost:3000",  # CRA default
    "http://127.0.0.1:5173",
    "http://127.0.0.1:3000",
]

# Feature flags
ENABLE_TRANSCRIPTION = True
ENABLE_DIARIZATION = True
ENABLE_EMOTION = True
ENABLE_FORMANTS = True
ENABLE_NOISE_PROFILE = True
