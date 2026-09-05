# NextScholar Audio Backend

Production-ready FastAPI backend for classroom audio analysis.

## Features

- Audio upload with automatic metadata extraction (duration, sample rate, channels, format)
- Background job processing with status tracking
- Audio transcription using faster-whisper with hallucination filtering
- Speaker matching via Zoom timeline JSON
- Hindi-to-English translation using Ollama
- Teacher-student interaction analysis
- Communication quality analysis
- Student performance classification
- Communication sentiment analysis (audio + text)
- Final comprehensive report generation
- SQLite persistence via SQLAlchemy

## Project Structure

```
backend/
├── app/
│   ├── main.py                    # FastAPI application entry point
│   ├── api/
│   │   ├── health.py              # Health check endpoint
│   │   ├── audio.py               # Upload and analyze endpoints
│   │   └── analysis.py            # Status and result endpoints
│   ├── services/
│   │   ├── audio_service.py       # Orchestrates full pipeline
│   │   ├── transcription_service.py  # Wraps existing test.py logic
│   │   ├── analysis_service.py    # Wraps existing analysis modules
│   │   └── report_service.py      # Report persistence
│   ├── tools/
│   │   ├── audio_processor.py     # FFmpeg conversion helpers
│   │   └── metadata.py            # Audio metadata extraction
│   ├── db/
│   │   ├── database.py            # SQLAlchemy engine/session
│   │   ├── models.py              # ORM models
│   │   ├── session.py             # Session factory
│   │   └── crud/
│   │       ├── audio.py
│   │       ├── transcript.py
│   │       ├── analysis.py
│   │       └── results.py
│   ├── schemas/
│   │   ├── audio.py
│   │   ├── analysis.py
│   │   └── results.py
│   ├── core/
│   │   └── config.py              # Environment configuration
│   └── existing_code/             # Preserved existing Python modules
│       ├── test.py
│       ├── hindi_to_english.py
│       ├── respond.py
│       ├── respond_detail.py
│       ├── extra_task.py
│       ├── final_report.py
│       ├── Type_of_conversation.py
│       ├── identidy_who_speaks.py
│       ├── indetification_of_studnet.py
│       ├── duration_of_conversesion.py
│       ├── number_of_interaction.py
│       ├── student_communication_type.py
│       ├── teacher_comunication_type.py
│       └── Duration_of_class.py
├── uploads/
├── outputs/
├── tests/
├── docs/
│   └── AUDIO_CODE_MAP.md
├── requirements.txt
├── .env.example
└── README.md
```

## Prerequisites

- Python 3.9+
- FFmpeg (for audio conversion)
- Ollama (local LLM runtime)
- At least 8GB RAM (for faster-whisper large-v3)

## Setup

1. Clone the repository and navigate to the backend directory:
   ```bash
   cd D:\Intership\NextSchlor\Backend_testing
   ```

2. Create a virtual environment:
   ```bash
   python -m venv venv
   venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Copy `.env.example` to `.env` and configure:
   ```bash
   copy .env.example .env
   ```

5. Ensure Ollama is running with the required model:
   ```bash
   ollama pull richardyoung/llama-3.2-3b-instruct-abliterated:Q4_K_M
   ollama serve
   ```

6. Start the FastAPI server:
   ```bash
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

## API Endpoints

### GET /health
Check service health, Ollama status, and database connectivity.

### POST /api/audio/upload
Upload an audio file for analysis.

**Request (multipart/form-data):**
- `file`: Audio file (m4a, mp3, wav, etc.)
- `timeline_json` (optional): Zoom meeting timeline JSON

**Response:**
```json
{
  "audio_id": "uuid",
  "filename": "recording.m4a",
  "status": "uploaded",
  "duration": 1234.5,
  "format": "WAV",
  "sample_rate": 16000,
  "channels": 1,
  "file_size": 45678900
}
```

### POST /api/audio/analyze
Start background analysis for a previously uploaded audio.

**Request (JSON):**
```json
{
  "audio_id": "uuid"
}
```

**Response:**
```json
{
  "job_id": "uuid",
  "status": "queued"
}
```

### GET /api/audio/status/{job_id}
Check analysis job status.

**Response:**
```json
{
  "job_id": "uuid",
  "status": "processing",
  "current_stage": "translation",
  "progress": 50.0,
  "error_message": null
}
```

### GET /api/audio/result/{job_id}
Retrieve completed analysis results.

**Response:**
```json
{
  "job_id": "uuid",
  "status": "completed",
  "audio": { ... },
  "transcript": { ... },
  "analysis": { ... }
}
```

### GET /api/audio/{audio_id}
Get audio file metadata.

## Audio Pipeline

```
REAL AUDIO FILE
    ↓
Audio Validation + Metadata Extraction
    ↓
FFmpeg Conversion (16kHz mono WAV)
    ↓
faster-whisper large-v3 Transcription
    ↓
Hallucination Filtering + Segment Cleaning
    ↓
Zoom Timeline Speaker Matching (if JSON provided)
    ↓
Hindi → English Translation (Ollama)
    ↓
Interaction Analysis (Ollama)
    ↓
Communication Quality Analysis (Ollama)
    ↓
Student Performance Analysis (Ollama)
    ↓
Communication Sentiment Analysis (librosa + Ollama)
    ↓
Final Comprehensive Report (Ollama)
    ↓
Structured JSON Result
```

## Database

SQLite database `classroom.db` with tables:

| Table | Purpose |
|-------|---------|
| audio_files | Uploaded audio metadata and processing status |
| transcripts | Generated transcripts |
| transcript_segments | Individual transcript segments with timestamps |
| speakers | Identified speakers from Zoom timeline |
| analysis_results | Analysis outputs by type |
| analysis_jobs | Background job tracking |

## Configuration

Environment variables (`.env`):

| Variable | Default | Description |
|----------|---------|-------------|
| OLLAMA_BASE_URL | http://localhost:11434 | Ollama server URL |
| OLLAMA_MODEL | richardyoung/llama-3.2-3b-instruct-abliterated:Q4_K_M | Default analysis model |
| OLLAMA_TRANSCRIPTION_MODEL | large-v3 | Whisper model size |
| DATABASE_URL | sqlite:///./classroom.db | SQLAlchemy database URL |
| UPLOAD_DIR | ./uploads | Audio upload directory |
| OUTPUT_DIR | ./outputs | Analysis output directory |
| TRANSCRIPTION_CHUNK_SIZE | 600 | Chunk size for long audio |
| LOG_LEVEL | INFO | Logging level |

## Testing

Run tests:
```bash
pytest tests/ -v
```

## Existing Code Integration

All existing Python analysis modules are preserved under `app/existing_code/` and wrapped by service classes. No analysis algorithms were rewritten.

- `test.py` → TranscriptionService (faster-whisper + hallucination filtering)
- `hindi_to_english.py` → AnalysisService.translate_hindi_to_english
- `respond.py` → AnalysisService.analyze_interactions
- `respond_detail.py` → AnalysisService.analyze_communication_quality
- `extra_task.py` → AnalysisService.analyze_student_performance
- `Type_of_conversation.py` → AnalysisService.analyze_communication_sentiment
- `final_report.py` → AnalysisService.generate_final_report

## Notes

- Speaker diarization: NOT IMPLEMENTED — speaker labels come exclusively from Zoom timeline JSON
- Video analysis: excluded per project rules (Duration_of_class.py preserved but not integrated)
- All processing uses local Ollama; no cloud APIs are used
- Long audio handling: faster-whisper processes full audio; chunking can be added at the pipeline level if needed
