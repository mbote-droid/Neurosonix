import numpy as np
from loguru import logger
from typing import List, Tuple
from models import DiarizationSegment
import librosa

class DiarizationEngine:
    """Speaker diarization: identify speaker regions in audio."""

    def __init__(self, sr: int = 16000, max_speakers: int = 4):
        self.sr = sr
        self.max_speakers = max_speakers
        logger.info(f"DiarizationEngine initialized (sr={sr}, max_speakers={max_speakers})")

    def detect_speech_regions(self, y: np.ndarray, sr: int) -> List[Tuple[float, float]]:
        """
        Simple speech activity detection (VAD) using energy-based approach.

        Returns: List of (start_sec, end_sec) tuples for speech regions
        """
        try:
            # Energy-based VAD: split audio into frames and detect high-energy regions
            frame_length = int(sr * 0.02)  # 20ms frames
            hop_length = int(sr * 0.01)    # 10ms stride

            rms = librosa.feature.rms(y=y, frame_length=frame_length, hop_length=hop_length)[0]
            energy_threshold = np.mean(rms) * 0.5  # Threshold at 50% of mean

            # Find speech regions
            active_frames = np.where(rms > energy_threshold)[0]

            if len(active_frames) == 0:
                logger.warning("No speech detected")
                return []

            # Merge adjacent frames into regions
            regions = []
            region_start = active_frames[0]
            region_end = active_frames[0]

            for frame in active_frames[1:]:
                if frame - region_end <= 3:  # Allow 3-frame gap
                    region_end = frame
                else:
                    # End current region
                    start_sec = librosa.frames_to_time(region_start, sr=sr, hop_length=hop_length)
                    end_sec = librosa.frames_to_time(region_end, sr=sr, hop_length=hop_length)
                    regions.append((start_sec, end_sec))
                    region_start = frame
                    region_end = frame

            # Finalize last region
            start_sec = librosa.frames_to_time(region_start, sr=sr, hop_length=hop_length)
            end_sec = librosa.frames_to_time(region_end, sr=sr, hop_length=hop_length)
            regions.append((start_sec, end_sec))

            logger.debug(f"Detected {len(regions)} speech regions")
            return regions
        except Exception as e:
            logger.error(f"Speech detection failed: {e}")
            return []

    def estimate_speakers(self, y: np.ndarray, sr: int) -> int:
        """
        Estimate number of speakers in audio (very simple heuristic).

        In a real system, this would use speaker embeddings (x-vectors, etc.).
        For now: analyze spectral changes to suggest speaker count.
        """
        try:
            # Compute MFCC to look for acoustic variations
            mfcc = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=13)

            # Calculate delta (change) in MFCCs
            mfcc_delta = librosa.feature.delta(mfcc)
            mfcc_delta_delta = librosa.feature.delta(mfcc_delta)

            # High variability suggests multiple speakers
            variability = np.mean(np.std(mfcc_delta_delta, axis=1))

            if variability > 5:
                estimated_speakers = min(4, int(variability / 3))  # Heuristic
            else:
                estimated_speakers = 1

            logger.debug(f"Estimated speakers: {estimated_speakers}")
            return estimated_speakers
        except Exception as e:
            logger.error(f"Speaker estimation failed: {e}")
            return 1

    def simple_diarization(
        self, y: np.ndarray, sr: int
    ) -> List[DiarizationSegment]:
        """
        Simple speaker diarization: detect speech regions + assign speaker IDs.

        Returns: List of DiarizationSegment objects (for UI swimlanes)

        Note: This is a basic heuristic. Real diarization uses speaker embeddings (pyannote).
        """
        try:
            logger.info("Starting simple diarization")

            regions = self.detect_speech_regions(y, sr)
            if not regions:
                logger.warning("No speech regions detected")
                return []

            estimated_speakers = self.estimate_speakers(y, sr)

            # Simple assignment: alternate speakers across regions
            segments = []
            for i, (start, end) in enumerate(regions):
                speaker_id = i % estimated_speakers
                segment = DiarizationSegment(
                    speaker_id=speaker_id,
                    timestamp_start=float(start),
                    timestamp_end=float(end),
                    text=None  # Will be filled in by transcription
                )
                segments.append(segment)

            logger.info(f"Diarization complete: {len(segments)} segments, {estimated_speakers} speakers")
            return segments
        except Exception as e:
            logger.error(f"Diarization failed: {e}")
            return []

    def diarization_with_pyannote(self, audio_path: str) -> List[DiarizationSegment]:
        """
        Use pyannote.audio for production-grade speaker diarization.

        Requires: pip install pyannote.audio
        """
        try:
            from pyannote.audio import Pipeline

            logger.info(f"Loading pyannote pipeline for {audio_path}")
            pipeline = Pipeline.from_pretrained(
                "pyannote/speaker-diarization-3.0",
                use_auth_token=False  # Public model, no auth needed
            )

            diarization = pipeline(audio_path)

            segments = []
            for turn, _, speaker in diarization.itertracks(yield_label=True):
                segment = DiarizationSegment(
                    speaker_id=int(speaker.replace("Speaker ", "")),
                    timestamp_start=turn.start,
                    timestamp_end=turn.end,
                    text=None
                )
                segments.append(segment)

            logger.info(f"Pyannote diarization complete: {len(segments)} segments")
            return segments
        except ImportError:
            logger.warning("pyannote.audio not installed; falling back to simple diarization")
            y, sr = librosa.load(audio_path, sr=self.sr, mono=True)
            return self.simple_diarization(y, sr)
        except Exception as e:
            logger.error(f"Pyannote diarization failed: {e}")
            y, sr = librosa.load(audio_path, sr=self.sr, mono=True)
            return self.simple_diarization(y, sr)
