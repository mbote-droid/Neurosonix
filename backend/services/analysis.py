import numpy as np
import librosa
from loguru import logger
from config import SAMPLE_RATE, SNR_EXCELLENT, SNR_USABLE
from models import QualityLevel, EmotionLabel
from typing import Tuple, Dict

class AudioAnalyzer:
    """Core audio analysis engine: SNR, emotion, formants, noise profile."""

    def __init__(self, sr: int = SAMPLE_RATE):
        self.sr = sr
        logger.debug(f"AudioAnalyzer initialized with sample_rate={sr}")

    def load_audio(self, audio_path: str) -> Tuple[np.ndarray, int]:
        """Load audio file, return (waveform, sample_rate)."""
        try:
            y, sr = librosa.load(audio_path, sr=self.sr, mono=True)
            logger.info(f"Loaded {audio_path}: {len(y)} samples, {sr} Hz")
            return y, sr
        except Exception as e:
            logger.error(f"Failed to load audio {audio_path}: {e}")
            raise

    def calculate_snr(self, y: np.ndarray, sr: int) -> float:
        """
        Calculate Signal-to-Noise Ratio in dB.

        Assumes first 0.5s is noise, rest is signal (reasonable for annotations).
        Formula: SNR_dB = 10 * log10(P_signal / P_noise)
        """
        try:
            noise_duration = int(sr * 0.5)
            noise_sample = y[:noise_duration]
            signal_sample = y[noise_duration:]

            p_noise = np.mean(noise_sample ** 2)
            p_signal = np.mean(signal_sample ** 2)

            if p_noise == 0 or p_signal == 0:
                logger.warning("Zero power detected; clamping to avoid log(0)")
                p_noise = max(p_noise, 1e-10)
                p_signal = max(p_signal, 1e-10)

            snr_db = 10 * np.log10(p_signal / p_noise)
            logger.debug(f"SNR calculated: {snr_db:.2f} dB")
            return float(snr_db)
        except Exception as e:
            logger.error(f"SNR calculation failed: {e}")
            return 0.0

    def get_quality_level(self, snr_db: float) -> QualityLevel:
        """Map SNR to quality traffic light."""
        if snr_db >= SNR_EXCELLENT:
            return QualityLevel.EXCELLENT
        elif snr_db >= SNR_USABLE:
            return QualityLevel.USABLE
        else:
            return QualityLevel.POOR

    def get_noise_profile(self, y: np.ndarray, sr: int) -> Dict[str, float]:
        """
        Estimate noise characteristics.
        Returns: spectral centroid, RMS energy, duration.
        """
        try:
            centroid = librosa.feature.spectral_centroid(y=y, sr=sr)[0]
            mean_centroid = float(np.mean(centroid))

            rms = librosa.feature.rms(y=y)[0]
            mean_rms = float(np.mean(rms))

            duration = librosa.get_duration(y=y, sr=sr)

            profile = {
                "spectral_centroid_hz": mean_centroid,
                "rms_energy": mean_rms,
                "duration_sec": float(duration),
            }
            logger.debug(f"Noise profile: {profile}")
            return profile
        except Exception as e:
            logger.error(f"Noise profile extraction failed: {e}")
            return {
                "spectral_centroid_hz": 0.0,
                "rms_energy": 0.0,
                "duration_sec": 0.0,
            }

    def analyze_formants(self, y: np.ndarray, sr: int) -> Tuple[float, float]:
        """
        Extract F1/F2 formant frequencies (vowel characteristics).

        Simple implementation via spectral peak detection.
        Returns: (f1_hz, f2_hz) or (None, None) if detection fails.
        """
        try:
            S = np.abs(librosa.stft(y))
            freqs = librosa.fft_frequencies(sr=sr)
            power = np.mean(S, axis=1)

            # Peak picking (conservative thresholds to avoid noise)
            peaks = librosa.util.peak_pick(
                power, pre_max=5, post_max=5, pre_avg=3, post_avg=3, delta=0.1, wait=10
            )

            f1 = float(freqs[peaks[0]]) if len(peaks) > 0 else None
            f2 = float(freqs[peaks[1]]) if len(peaks) > 1 else None

            logger.debug(f"Formants detected: F1={f1}, F2={f2}")
            return f1, f2
        except Exception as e:
            logger.warning(f"Formant analysis failed: {e}")
            return None, None

    def estimate_emotion(self, y: np.ndarray, sr: int) -> Tuple[EmotionLabel, float]:
        """
        Estimate emotion from audio features.

        Uses RMS energy, spectral centroid, zero-crossing rate as heuristics.
        Returns: (emotion, confidence)
        """
        try:
            rms = np.mean(librosa.feature.rms(y=y))
            centroid = np.mean(librosa.feature.spectral_centroid(y=y, sr=sr))
            zcr = np.mean(librosa.feature.zero_crossing_rate(y))

            # Heuristic emotion mapping
            if rms > 0.1 and centroid > 2000:
                emotion = EmotionLabel.EXCITED
                confidence = 0.7
            elif rms < 0.05:
                emotion = EmotionLabel.CALM
                confidence = 0.6
            elif centroid < 1500 and rms > 0.07:
                emotion = EmotionLabel.SAD
                confidence = 0.6
            elif rms > 0.08 and centroid > 3000:
                emotion = EmotionLabel.ANGRY
                confidence = 0.7
            else:
                emotion = EmotionLabel.NEUTRAL
                confidence = 0.8

            logger.debug(f"Emotion: {emotion} (confidence={confidence})")
            return emotion, float(confidence)
        except Exception as e:
            logger.error(f"Emotion estimation failed: {e}")
            return EmotionLabel.NEUTRAL, 0.0

    def analyze_full(self, audio_path: str) -> Dict:
        """Run full analysis pipeline."""
        logger.info(f"Starting full analysis on {audio_path}")

        y, sr = self.load_audio(audio_path)
        snr = self.calculate_snr(y, sr)
        quality = self.get_quality_level(snr)
        noise_profile = self.get_noise_profile(y, sr)
        f1, f2 = self.analyze_formants(y, sr)
        emotion, emotion_conf = self.estimate_emotion(y, sr)

        result = {
            "snr_db": snr,
            "quality": quality.value,
            "spectral_centroid_hz": noise_profile["spectral_centroid_hz"],
            "rms_energy": noise_profile["rms_energy"],
            "duration_sec": noise_profile["duration_sec"],
            "f1_hz": f1,
            "f2_hz": f2,
            "emotion": emotion.value,
            "emotion_confidence": emotion_conf,
        }

        logger.info(f"Analysis complete: {result}")
        return result
