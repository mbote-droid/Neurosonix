# NeuroSonix: How It Works

## Overview
NeuroSonix is a **locale-agnostic audio annotation pipeline** for AI training data. It analyzes audio, detects speakers, generates transcriptions, and stores structured annotations in JSON/CSV format—all with transparent, physics-based quality metrics.

## Runtime Execution Flow

### Phase 1: Audio Upload & File Handling
1. **User uploads audio file** via POST `/api/audio/upload`
2. **File validation** — check filename, size, format (WAV/MP3/FLAC)
3. **Save to disk** — write to `uploads/` directory with UUID filename
4. **Log metadata** — record filename, size, timestamp

### Phase 2: Audio Analysis Pipeline
5. **Load audio** — librosa reads file at 16 kHz mono
6. **Calculate SNR (Signal-to-Noise Ratio)**
   - Split audio: first 0.5s = noise, rest = signal
   - Calculate RMS power for each region: P = mean(y²)
   - SNR_dB = 10 * log₁₀(P_signal / P_noise)
   - Return float SNR value in decibels

7. **Determine quality level** — map SNR to traffic light
   - Green (Excellent): SNR ≥ 20 dB
   - Yellow (Usable): 10 dB ≤ SNR < 20 dB
   - Red (Poor): SNR < 10 dB

8. **Extract noise profile**
   - Spectral centroid: center of mass of spectrum (Hz)
   - RMS energy: root mean square of waveform
   - Duration: computed from sample count

9. **Analyze formants (F1/F2)**
   - Compute STFT (short-time Fourier transform)
   - Find spectral peaks via librosa.util.peak_pick
   - Map peaks to frequencies (F1, F2 for vowel characteristics)
   - Return Hz values or None if detection fails

10. **Estimate emotion** — heuristic classification
    - RMS energy + spectral centroid + zero-crossing rate
    - Rules: high RMS + high centroid = Excited; low RMS = Calm, etc.
    - Return (emotion label, confidence 0.0–1.0)

### Phase 3: Speech Recognition
11. **Transcribe audio** — OpenAI Whisper model
    - Load Whisper "base" model on first call (lazy load)
    - If Whisper unavailable, return fallback message
    - Run transcription on audio file
    - Return full transcript text or error message

### Phase 4: Speaker Diarization
12. **Detect speech regions** — energy-based VAD (Voice Activity Detection)
    - Split into 20ms frames with 10ms stride
    - Compute RMS for each frame
    - Threshold at 50% of mean energy
    - Merge adjacent frames (allow 3-frame gap)
    - Return list of (start_sec, end_sec) tuples

13. **Estimate speaker count** — MFCC variability heuristic
    - Extract MFCCs (Mel-frequency cepstral coefficients)
    - Compute delta and delta-delta
    - High variance suggests multiple speakers
    - Return integer (1–4)

14. **Simple diarization** — alternate speaker IDs across regions
    - Assign Speaker 0/1/2/3 in round-robin
    - Return DiarizationSegment objects with (speaker_id, start, end, text=None)
    - *Alternative*: use pyannote.audio for production-grade diarization

### Phase 5: Response Assembly
15. **Aggregate results** into AudioAnalysis object:
    - file_id, filename, duration, sample_rate
    - snr_db, quality, emotion, emotion_confidence
    - spectral_centroid_hz, rms_energy, f1_hz, f2_hz
    - transcription (full text)
    - diarization_segments (list of speaker regions)

16. **Return JSON response** to frontend with all analysis data

---

## Phase 6: User Annotation (Client-Side)
17. **Frontend displays**:
    - Waveform visualization (WebAudio API, 60 FPS)
    - SNR quality indicator (traffic light)
    - Transcription text
    - Emotion badge
    - Formant plot (F1/F2)
    - Speaker swimlanes (4 draggable lanes for manual correction)

18. **User manually annotates**:
    - Drag speech regions to correct speaker lane
    - Add/edit transcription text per segment
    - Select emotion (Neutral/Calm/Excited/Sad/Angry)
    - Rate clarity (1–5 slider)
    - Add optional notes

19. **POST annotations** to `/api/annotate/{file_id}` with AnnotationCreate payload:
    - speaker, timestamp_start, timestamp_end, text, emotion, clarity, confidence, notes

### Phase 7: Persistence & Export
20. **Save annotations** to disk:
    - Load existing `annotations/{file_id}.json` (or create)
    - Append new annotation to list
    - Write back to JSON

21. **Export request** via `/api/annotate/{file_id}/export/{format_type}`:
    - **JSON export**: Full metadata + annotations (nested structure)
    - **CSV export**: Tabular format (one row per annotation)
      - Columns: file_id, filename, speaker, timestamp_start, timestamp_end, text, emotion, clarity, confidence, notes

22. **Return export** to user as downloadable file

---

## Phase 8: Agentic Evaluation Pipeline

Scores a voice-agent conversation end to end. Input is a transcript (from the
Whisper/Gemini step above, or pasted directly) plus a chosen role-play scenario.

23. **User submits evaluation** via POST `/api/evaluate/` with `scenario_id`,
    `transcript`, and optional `model_name` / `audio_file_id`.
24. **Resolve scenario** — look up the `ScenarioTemplate` by id (persona,
    policies, user goal) from the scenario library; unknown id → 404.
25. **Resolve LLM provider** — `get_default_client()` reads
    `NEUROSONIX_LLM_PROVIDER` (default `anthropic`). With a resolvable API key
    it returns an `AnthropicLLMClient` (model `claude-opus-4-8`); otherwise a
    `NullLLMClient` so the pipeline runs fully offline.
26. **Role-play agent replies** — the transcript is fed as the user turn to an
    agent primed with the scenario's system prompt. With an LLM, it generates a
    reply; offline, it returns a deterministic, role-appropriate reply. The
    result is flagged `degraded` when no LLM was used.
27. **Five evaluator agents score the reply** — one per dimension: Task
    Completion, Conversational Naturalness, Audio Comprehension, Instruction
    Adherence, Technical Clarity. Each uses the LLM with structured JSON output
    (`output_config.format`, guaranteed-parseable) against its rubric; on any
    LLM failure it falls back to a transparent per-dimension heuristic. Scores
    are clamped to 1–5 and confidence to 0.0–1.0.
28. **Synthesize** — combine the five scores into one confidence-weighted mean
    (unweighted mean if all confidence is zero; scale midpoint if empty).
29. **Assemble `EvaluationResult`** — id, scenario, model, transcript, reply,
    per-agent scores, synthesized score, and an overall `degraded` flag (true
    if the reply or any score was degraded).
30. **Persist (best-effort)** — save to the `evaluation_results` table via
    SQLAlchemy `merge` (idempotent on id). A persistence failure is logged and
    swallowed so it never breaks the response.
31. **Return JSON** to the frontend, which renders per-dimension bars, the
    synthesized score, the agent reply, and a live/offline mode badge.

## Phase 9: Model Comparison

32. **User submits comparison** via POST `/api/evaluate/compare` with a
    `scenario_id` and a `model_transcripts` map (e.g. Whisper vs Gemini
    transcripts of the same audio).
33. **Evaluate each model** — the swarm (steps 26–29) runs once per transcript,
    tagged with that model's name.
34. **Rank and pick winner** — highest synthesized score wins; ties break
    deterministically toward the first model in insertion order. Persist to the
    `model_comparisons` table.
35. **Return `ModelComparison`** — per-model entries with per-dimension scores
    and the winner, rendered as a side-by-side table with the winner highlighted.

**History & export:** `GET /api/evaluate/results` (and `/results/{id}`) and
`GET /api/evaluate/comparisons` return stored records newest-first for benchmark
review and export. `GET /api/evaluate/health` reports whether a live LLM backs
the swarm.

---

## Key Design Decisions

### Why Energy-Based VAD (Not AI)?
- **Simplicity**: Works offline, no models
- **Speed**: Runs in milliseconds
- **Fallback**: Graceful degradation if Whisper unavailable
- **Alternative**: Can swap in Silero VAD or pyannote for production

### Why Emotion is Heuristic?
- Avoids training a separate classifier
- Uses audio features that humans understand (energy, brightness)
- Confidence scores are honest about accuracy
- User can override in UI

### Why Formants?
- **Locale-agnostic**: F1/F2 are language-neutral vowel features
- **Visual**: Can plot on screen for users to evaluate accents
- **Physics-grounded**: Matches linguistic reality

### Why Signal-to-Noise in the "Quality Traffic Light"?
- **User-facing metric**: Non-technical people understand "green = good"
- **Physics-valid**: SNR is the standard audio quality measure
- **Thresholds**: 20 dB (studio), 10 dB (usable), <10 dB (unusable) are industry standard

### Why SQLite + JSON File Backup?
- **Local-first**: No server dependency
- **Simple**: No migrations, no ORM overhead
- **Durable**: JSON is human-readable and portable
- **Offline**: Works without network

---

## Error Handling & Graceful Degradation

| Component | Failure | Fallback |
|-----------|---------|----------|
| Whisper (transcription) | Not installed | Return "[Transcription unavailable]" |
| Pyannote (diarization) | Not installed | Fall back to simple VAD-based diarization |
| Formant detection | No peaks found | Return None for F1/F2 |
| Emotion classification | NaN values | Default to Neutral, confidence 0.0 |
| SNR calculation | Zero power | Clamp to 1e-10 to avoid log(0) |
| LLM provider (role-play/evaluators) | No API key / SDK / API error | `NullLLMClient`; deterministic reply + per-dimension heuristic scores, result flagged `degraded` |
| Result persistence | DB write fails | Log and swallow; evaluation still returned to the caller |
| Model output out of range | Score >5 or confidence >1 | Clamp to 1–5 / 0.0–1.0 rather than reject |

---

## Performance Characteristics (8 GB RAM, CPU-only)

| Task | Time (2-min audio) | Memory |
|------|-------------------|--------|
| Load & analysis | ~2 sec | ~50 MB |
| Transcription (Whisper base) | ~10 sec | ~400 MB |
| Formants | ~0.5 sec | ~100 MB |
| Diarization | ~3 sec | ~100 MB |
| **Total** | **~15 sec** | **~500 MB peak** |

✓ Safe on 8 GB laptop (plenty of headroom)

---

## Data Flow Diagram

```
User Upload
    ↓
[File Save]
    ↓
[Audio Analysis] ← librosa + scipy + numpy
    ├→ SNR Meter
    ├→ Noise Profile
    ├→ Formants (F1/F2)
    └→ Emotion Heuristic
    ↓
[Transcription] ← Whisper
    ↓
[Diarization] ← VAD + speaker estimation
    ↓
[JSON Response] → Frontend
    ↓
[User Annotation] (browser-side)
    ↓
[POST Annotations] → Backend
    ↓
[Save to JSON]
    ↓
[Export] (JSON/CSV) → User
```

---

## Future Extensions

1. **Pyannote Integration**: Swap simple_diarization() for pyannote-audio for speaker embeddings
2. **LLM-based Correction**: Use Claude to suggest emoji transcription corrections
3. **Speaker Embedding**: Cluster voices to identify same speaker across files
4. **Confidence Scoring**: Machine-learned confidence on annotation consistency
5. **Batch Processing**: Queue audio files for offline analysis
6. **Web UI**: React frontend with waveform, swimlanes, and real-time feedback

---

**Versioning**: NeuroSonix v0.1.0 (July 2026)
**Author**: Samuel Mbote
**License**: [To be determined]
