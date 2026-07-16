from fastapi import APIRouter, UploadFile, File, HTTPException
from loguru import logger
from pathlib import Path
import uuid
from config import UPLOAD_DIR
from services.analysis import AudioAnalyzer
from services.transcription import TranscriptionEngine
from services.diarization import DiarizationEngine
from models import AudioAnalysis, DiarizationSegment

router = APIRouter(prefix="/api/audio", tags=["audio"])

analyzer = AudioAnalyzer()
transcriber = TranscriptionEngine()
diarizer = DiarizationEngine()

@router.post("/upload")
async def upload_audio(file: UploadFile = File(...)):
    """
    Upload and analyze audio file.

    Returns: Full audio analysis including SNR, emotion, transcription, diarization
    """
    try:
        logger.info(f"Upload requested: {file.filename}")

        # Validate file
        if not file.filename:
            raise HTTPException(status_code=400, detail="No filename provided")

        # Save file
        file_id = str(uuid.uuid4())
        file_ext = Path(file.filename).suffix or ".wav"
        file_path = UPLOAD_DIR / f"{file_id}{file_ext}"

        contents = await file.read()
        with open(file_path, "wb") as f:
            f.write(contents)

        logger.info(f"File saved: {file_path}")

        # Run analysis pipeline
        analysis_result = analyzer.analyze_full(str(file_path))
        transcription = transcriber.transcribe(str(file_path))

        # Load audio for diarization
        y, sr = analyzer.load_audio(str(file_path))
        diarization_segments = diarizer.simple_diarization(y, sr)

        # Build response
        response = AudioAnalysis(
            file_id=file_id,
            filename=file.filename,
            duration_sec=analysis_result["duration_sec"],
            sample_rate=sr,
            snr_db=analysis_result["snr_db"],
            quality=analysis_result["quality"],
            emotion=analysis_result["emotion"],
            emotion_confidence=analysis_result["emotion_confidence"],
            spectral_centroid_hz=analysis_result["spectral_centroid_hz"],
            rms_energy=analysis_result["rms_energy"],
            f1_hz=analysis_result["f1_hz"],
            f2_hz=analysis_result["f2_hz"],
            transcription=transcription,
            diarization_segments=diarization_segments,
        )

        logger.info(f"Upload and analysis complete for {file_id}")
        return response
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Upload failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/health")
async def health():
    """Health check endpoint."""
    return {
        "status": "ok",
        "transcriber_available": transcriber.health_check(),
    }
