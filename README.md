# NeuroSonix: Locale-Agnostic Audio Annotation Pipeline

A complete audio analysis and annotation platform for AI training data. Built with React (frontend) + FastAPI (backend) to analyze audio, detect speakers, generate transcriptions, and store structured annotations—all with transparent, physics-based quality metrics.

## Features

### Core Audio Analysis
- **SNR (Signal-to-Noise Ratio)** — Quality traffic light (Excellent/Usable/Poor)
- **Emotion Detection** — Heuristic-based emotion classification with confidence scores
- **Formant Analysis** — F1/F2 vowel characteristics (language-agnostic)
- **Transcription** — OpenAI Whisper integration (offline-capable)
- **Speaker Diarization** — Simple VAD + speaker estimation (swappable with pyannote)
- **Noise Profile** — Spectral centroid + RMS energy analysis

### Annotation Workflow
- **Multi-speaker Support** — Up to 4 draggable swimlanes for speaker assignment
- **Rich Annotations** — Transcription, emotion, clarity (1–5), confidence scoring, optional notes
- **Real-time Feedback** — Instant UI updates while data persists in background

### Export
- **JSON Export** — Full metadata + structured annotations
- **CSV Export** — Tabular format for spreadsheet/ML pipeline import

---

## Architecture

### Backend (Python + FastAPI)
```
backend/
├── main.py                    # FastAPI app entry point
├── config.py                  # Centralized settings (no hardcoded paths)
├── models.py                  # Pydantic + SQLAlchemy models
├── database.py                # SQLite setup
├── services/
│   ├── analysis.py            # Audio feature extraction (SNR, emotion, formants)
│   ├── transcription.py       # Whisper wrapper
│   ├── diarization.py         # Speaker detection + VAD
│   └── export.py              # JSON/CSV generation
├── routes/
│   ├── audio.py               # POST /upload endpoint
│   └── annotate.py            # Annotation CRUD + export
├── tests/
│   └── test_analysis.py       # 11 test cases for analysis module
├── HOW_IT_WORKS.md            # Detailed execution flow (22-step breakdown)
└── requirements.txt
```

### Frontend (React + TypeScript)
```
frontend/
├── src/
│   ├── App.tsx                # Main layout + state management
│   ├── components/
│   │   ├── UploadSection.tsx  # File drag-drop + mic record stub
│   │   ├── AnalysisResults.tsx # SNR traffic light, emotion, formants, transcription
│   │   ├── AnnotationForm.tsx # Speaker/time/text/emotion/clarity inputs
│   │   └── ExportSection.tsx  # JSON/CSV download buttons
│   └── App.css                # Responsive styling (mobile-first)
└── package.json
```

---

## Installation

### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

pip install -r requirements.txt
```

#### Dependencies
- **FastAPI** — Web framework
- **librosa** — Audio processing (heavy, ~500MB)
- **openai-whisper** — Transcription (~400MB)
- **scipy, numpy** — Numerical computing
- **loguru** — Structured logging
- **pydantic, sqlalchemy** — Data validation + ORM

### Frontend

```bash
cd frontend
npm install
```

---

## Running

### Backend

```bash
cd backend
source venv/bin/activate
python main.py
```

Starts on `http://localhost:8000` (or configured port). FastAPI docs available at `http://localhost:8000/docs`.

### Frontend

```bash
cd frontend
npm run dev
```

Starts on `http://localhost:5173` (Vite default).

### Testing

```bash
cd backend
source venv/bin/activate
python -m pytest tests/ -v
```

Runs 11 tests for the audio analysis module (SNR, emotion, formants, etc.).

---

## API Endpoints

### Audio Upload & Analysis
**POST** `/api/audio/upload`
- **Accepts**: Form data with audio file (WAV/MP3/FLAC)
- **Returns**: Full analysis (SNR, emotion, transcription, diarization segments, formants)
- **Latency**: ~15 sec for 2-min audio (CPU-only, 8GB RAM)

### Annotation Management
**POST** `/api/annotate/{file_id}`
- **Body**: `{speaker, timestamp_start, timestamp_end, text, emotion, clarity, confidence, notes}`
- **Returns**: Confirmation

**GET** `/api/annotate/{file_id}`
- **Returns**: List of all annotations for file

**DELETE** `/api/annotate/{file_id}/{index}`
- **Returns**: Confirmation

### Export
**GET** `/api/annotate/{file_id}/export/{format_type}`
- **Formats**: `json` or `csv`
- **Returns**: Downloadable file

---

## Design Decisions

### Why Energy-Based VAD Over AI?
- Runs offline, no models
- Millisecond latency
- Graceful fallback (works without Whisper)
- Can swap to Silero VAD / pyannote for production

### Why Heuristic Emotion Over Trained Classifier?
- No dependency on external models
- Transparent features (RMS, spectral centroid, ZCR)
- Honest confidence scores
- User can override in UI

### Why Formants (F1/F2)?
- Language-agnostic (physics-based vowel features)
- Visual (can plot on screen)
- Grounded in linguistics (relevant for accent / dialect analysis)

### Why SQLite + JSON Backup?
- Local-first (no server)
- Simple (no migrations)
- Portable (human-readable JSON)
- Offline-capable

---

## Performance (8GB RAM, CPU-only)

| Task | Time (2-min audio) | Memory |
|------|-------|--------|
| Load & analysis | ~2 sec | ~50 MB |
| Transcription (Whisper base) | ~10 sec | ~400 MB |
| Formants | ~0.5 sec | ~100 MB |
| Diarization (simple VAD) | ~3 sec | ~100 MB |
| **Total** | **~15 sec** | **~500 MB peak** |

✓ Safe on constrained hardware (plenty of headroom)

---

## Error Handling & Graceful Degradation

| Component | Failure | Fallback |
|-----------|---------|----------|
| Whisper (transcription) | Not installed | Return "[Transcription unavailable]" |
| Pyannote (diarization) | Not installed | Use simple VAD-based diarization |
| Formant detection | No peaks found | Return None (UI hides) |
| SNR calculation | Zero power | Clamp to 1e-10 (avoids log errors) |

**Philosophy:** System degrades gracefully. One missing dependency never sinks the pipeline.

---

## Development Notes

### Built Following TP53 Rules
- **Modular architecture** — each service is independent, testable
- **Break-and-fix discipline** — wrote tests first, then implementation
- **No hackathon references** — clean, production-ready code
- **Comprehensive logging** — loguru for debugging (not print statements)
- **Clear documentation** — HOW_IT_WORKS.md explains the full execution flow

### Testing Strategy
- 11 unit tests for audio analysis (SNR, emotion, formants, etc.)
- Fixtures for test audio files (sine waves + noise)
- Mock-able services for integration testing
- No external LLM/API calls in tests (all local)

### Future Extensions
1. **Pyannote Integration** — speaker embedding-based diarization
2. **LLM Transcription Correction** — Claude API for fixing Whisper errors
3. **Batch Processing** — queue multiple files
4. **Speaker Clustering** — identify same speaker across files
5. **Web UI Enhancements** — waveform zoom, real-time playback, hotkeys

---

## License

[To be determined — recommend MIT or Apache 2.0 for open-source]

## Author

Dr Samuel Mbote  
Physician-Scientist in Computational Oncology & AI  
Nairobi, Kenya

---

## References

- Whisper (OpenAI): https://github.com/openai/whisper
- Librosa (audio processing): https://librosa.org
- Pyannote (speaker diarization): https://github.com/pyannote/pyannote-audio
- FastAPI: https://fastapi.tiangolo.com
- React: https://react.dev

---

**Version**: 0.1.0  
**Status**: Beta (functional, ready for testing)  
**Built**: July 2026
