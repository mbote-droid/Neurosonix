import pytest
import numpy as np
from pathlib import Path
import soundfile as sf
from services.analysis import AudioAnalyzer
from models import QualityLevel, EmotionLabel
import tempfile
import os
import time

@pytest.fixture
def analyzer():
    """Provide an AudioAnalyzer instance."""
    return AudioAnalyzer(sr=16000)

@pytest.fixture
def test_audio_file():
    """Generate a test audio file (sine wave)."""
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        sr = 16000
        duration = 2  # 2 seconds
        freq = 440  # A4 note
        t = np.linspace(0, duration, sr * duration)
        y = np.sin(2 * np.pi * freq * t) * 0.3  # 30% amplitude

        sf.write(f.name, y, sr)
        yield f.name

        # Windows file locking: wait before cleanup
        time.sleep(0.1)
        try:
            os.remove(f.name)
        except OSError:
            pass  # File might be locked; ignore

@pytest.fixture
def low_snr_audio_file():
    """Generate a noisy audio file."""
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        sr = 16000
        duration = 2
        # Heavy noise
        y = np.random.randn(sr * duration) * 0.5
        sf.write(f.name, y, sr)
        yield f.name

        # Windows file locking: wait before cleanup
        time.sleep(0.1)
        try:
            os.remove(f.name)
        except OSError:
            pass  # File might be locked; ignore

class TestAudioAnalyzer:
    """Test suite for AudioAnalyzer."""

    def test_init(self, analyzer):
        """Test initialization."""
        assert analyzer.sr == 16000

    def test_load_audio(self, analyzer, test_audio_file):
        """Test audio loading."""
        y, sr = analyzer.load_audio(test_audio_file)
        assert len(y) > 0
        assert sr == 16000

    def test_load_audio_missing_file(self, analyzer):
        """Test loading non-existent file."""
        with pytest.raises(Exception):
            analyzer.load_audio("/nonexistent/path.wav")

    def test_calculate_snr_valid(self, analyzer, test_audio_file):
        """Test SNR calculation on clean audio."""
        y, sr = analyzer.load_audio(test_audio_file)
        snr = analyzer.calculate_snr(y, sr)
        assert isinstance(snr, float)
        assert snr > 0  # Should be positive for clean signal

    def test_calculate_snr_noisy(self, analyzer, low_snr_audio_file):
        """Test SNR calculation on noisy audio."""
        y, sr = analyzer.load_audio(low_snr_audio_file)
        snr = analyzer.calculate_snr(y, sr)
        assert isinstance(snr, float)
        # Noisy audio should have lower SNR
        assert snr < 20

    def test_get_quality_level_excellent(self, analyzer):
        """Test quality level mapping (excellent)."""
        quality = analyzer.get_quality_level(25.0)
        assert quality == QualityLevel.EXCELLENT

    def test_get_quality_level_usable(self, analyzer):
        """Test quality level mapping (usable)."""
        quality = analyzer.get_quality_level(15.0)
        assert quality == QualityLevel.USABLE

    def test_get_quality_level_poor(self, analyzer):
        """Test quality level mapping (poor)."""
        quality = analyzer.get_quality_level(5.0)
        assert quality == QualityLevel.POOR

    def test_get_noise_profile(self, analyzer, test_audio_file):
        """Test noise profile extraction."""
        y, sr = analyzer.load_audio(test_audio_file)
        profile = analyzer.get_noise_profile(y, sr)

        assert "spectral_centroid_hz" in profile
        assert "rms_energy" in profile
        assert "duration_sec" in profile
        assert profile["spectral_centroid_hz"] > 0
        assert profile["rms_energy"] > 0
        assert profile["duration_sec"] > 0

    def test_analyze_formants(self, analyzer, test_audio_file):
        """Test formant analysis."""
        y, sr = analyzer.load_audio(test_audio_file)
        f1, f2 = analyzer.analyze_formants(y, sr)

        # May be None for very short audio, but should be floats or None
        assert f1 is None or isinstance(f1, float)
        assert f2 is None or isinstance(f2, float)

    def test_estimate_emotion(self, analyzer, test_audio_file):
        """Test emotion estimation."""
        y, sr = analyzer.load_audio(test_audio_file)
        emotion, confidence = analyzer.estimate_emotion(y, sr)

        assert isinstance(emotion, EmotionLabel)
        assert isinstance(confidence, float)
        assert 0.0 <= confidence <= 1.0

    def test_analyze_full(self, analyzer, test_audio_file):
        """Test full analysis pipeline."""
        result = analyzer.analyze_full(test_audio_file)

        assert "snr_db" in result
        assert "quality" in result
        assert "emotion" in result
        assert "duration_sec" in result
        assert result["quality"] in [q.value for q in QualityLevel]
        assert result["emotion"] in [e.value for e in EmotionLabel]

    def test_analyze_full_returns_dict(self, analyzer, test_audio_file):
        """Test that analyze_full returns all expected keys."""
        result = analyzer.analyze_full(test_audio_file)

        expected_keys = [
            "snr_db", "quality", "spectral_centroid_hz", "rms_energy",
            "duration_sec", "f1_hz", "f2_hz", "emotion", "emotion_confidence"
        ]
        for key in expected_keys:
            assert key in result, f"Missing key: {key}"
