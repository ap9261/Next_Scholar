# Audio Code Map

This document maps every existing Python file to its actual purpose, functions, inputs, outputs, dependencies, and the planned backend component that will wrap it.

| File | Purpose | Main Functions | Input | Output | Dependencies | Backend Component |
| ---- | ------- | -------------- | ----- | ------ | ------------ | ----------------- |
| test.py | Primary audio-to-text transcription with hallucination prevention and Zoom timeline speaker matching | `transcribe_with_faster_whisper_large()`, `match_with_speakers()`, `process_and_clean_segments()`, `save_transcription()`, `detect_hallucination()`, `convert_to_wav()`, `load_zoom_timeline()`, `get_speaker_intervals()` | Audio file (m4a/mp3/wav), optional Zoom timeline JSON | Segments with start/end/text/speaker, TXT transcript, JSON transcript | faster-whisper, ffmpeg (subprocess), collections, re, json, os | `app/services/transcription_service.py` (wraps existing logic without rewriting it) |
| identidy_who_speaks.py | Transcribe audio with faster-whisper and match speakers using Zoom timeline JSON | `transcribe_with_speakers()`, `match_transcription_with_speakers()`, `get_speaker_intervals()`, `get_speaker_at_time()`, `who_spoke_at()`, `load_zoom_timeline()` | Audio file, Zoom timeline JSON | Matched segments with speaker labels, TXT/JSON output | faster-whisper, json, collections | Existing code preserved under `app/existing_code/`; speaker matching logic reused via tools if needed |
| indetification_of_studnet.py | Identify teacher and student names from Zoom timeline JSON | Script-level logic: loads JSON, counts users, identifies teacher by most common user, lists students | Zoom timeline JSON | Printed teacher name and student names; no programmatic return | json, collections.Counter | Not directly integrated as a standalone service; teacher/student identification logic is used by other modules and preserved in `app/existing_code/` |
| duration_of_conversesion.py | Calculate total speaking duration per user from Zoom timeline JSON | Script-level logic: loads JSON, tracks speaker on/off intervals, sums durations per user, separates teacher vs students | Zoom timeline JSON | Printed per-user durations; no programmatic return | json, collections.defaultdict | Duration analysis tool under `app/tools/` if needed; otherwise preserved in `app/existing_code/` |
| number_of_interaction.py | Count teacher-student turn-taking interactions from Zoom timeline JSON | Script-level logic: loads JSON, detects speaker changes between teacher and students, counts interactions per student | Zoom timeline JSON | Printed interaction counts per student; no programmatic return | json, collections.defaultdict | Interaction counting logic preserved in `app/existing_code/`; can be wrapped if needed |
| hindi_to_english.py | Translate Hindi transcript segments to English using Ollama; filter disturbances and non-subject text | `translate_to_english()`, `load_transcript()`, `is_disturbance_text()`, `is_valid_hindi_text()`, `is_subject_related()`, `clean_text()`, `format_time()` | Transcript JSON (with Hindi text segments), Ollama model | Translated conversation JSON/TXT with hindi+english+speaker+time, English-only JSON/TXT | ollama, json, re, collections, os | `app/services/translation_service.py` |
| respond.py | Analyze teacher-student interactions, response rates, unresponded questions; generate LLM summaries for unresponded questions | `analyze_interactions()`, `identify_teacher()`, `load_transcript()`, `generate_llm_summary()`, `generate_interaction_report()`, `save_json_output()` | Translated conversation JSON, Ollama model | Interaction analysis JSON/TXT with summary, unresponded questions, per-student stats | ollama, json, re, collections, os | `app/services/interaction_service.py` |
| respond_detail.py | Analyze communication quality (response quality, question quality) using Ollama; generate detailed reports | `analyze_communication_quality()`, `assess_response_quality()`, `assess_question_quality()`, `identify_teacher()`, `load_transcript()`, `generate_quality_report()`, `save_quality_json()` | Translated conversation JSON, Ollama model | Communication quality JSON/TXT with quality assessments, response times, recommendations | ollama, json, re, collections, os | `app/services/communication_quality_service.py` |
| extra_task.py | Classify students as Sharp/Average/Struggling/Critical based on performance; classify communication as Useful/Distraction using Ollama | `analyze_student_performance()`, `classify_student_type()`, `classify_communication_type()`, `evaluate_answer_quality()`, `identify_teacher()`, `load_transcript()`, `generate_performance_report()`, `save_performance_json()` | Translated conversation JSON, Ollama model | Student performance JSON/TXT with classifications, useful/distraction counts, recommendations | ollama, json, re, collections, os | `app/services/student_performance_service.py` |
| student_communication_type.py | Analyze per-student sentiment from audio using librosa features (energy, pitch, zero-crossing rate) | `analyze_student_sentiment()`, `get_sentiment()`, `extract_speaker_timeline()` | Audio file (wav), Zoom timeline JSON | Per-student sentiment percentages (positive/neutral/negative) and overall sentiment | librosa, numpy, json, collections | `app/tools/audio_sentiment.py` (audio-based analysis) |
| teacher_comunication_type.py | Analyze entire class sentiment from audio using librosa pitch/energy features; segment-level classification | `analyze_entire_class()`, `get_sentiment()` | Audio file (wav), optional Zoom timeline JSON | Overall class sentiment, engagement/negativity scores, per-minute breakdown, segment results | librosa, numpy, json, collections | `app/tools/class_sentiment.py` (audio-based analysis) |
| Type_of_conversation.py | Classify conversation segments as Positive/Negative/Neutral using both text (Ollama) and audio pitch features (librosa) | `classify_communication()`, `extract_pitch_features()`, `get_pitch_sentiment()`, `parse_classifications()`, `analyze_sentiment_patterns()`, `generate_systematic_report()`, `identify_teacher()`, `load_transcript()` | Transcript JSON, audio file (wav), Ollama model | Communication analysis report with text+audio sentiment, per-student/teacher breakdowns, recommendations | ollama, librosa, numpy, json, re, collections, os | `app/services/communication_sentiment_service.py` |
| final_report.py | Generate a comprehensive final conclusion report using Ollama by aggregating all prior analysis JSON outputs | `generate_comprehensive_analysis()`, `extract_interaction_insights()`, `extract_quality_insights()`, `extract_performance_insights()`, `extract_translation_insights()`, `generate_final_report()`, `save_final_json()`, `load_all_analyses()` | Multiple analysis JSON files (interaction, communication quality, student performance, translated conversation), Ollama model | Final conclusion TXT report and JSON with summary metrics, student performance, and LLM-generated conclusion | ollama, json, collections, os, datetime | `app/services/final_report_service.py` |
| Duration_of_class.py | Calculate video duration using OpenCV (video-only; excluded from audio backend per project rules) | Script-level logic: opens video with cv2, reads fps and frame count, computes duration | Video file (mp4) | Printed video duration (minutes, seconds) | cv2 | NOT INTEGRATED (video-only) |

## Actual Pipeline Discovered from Code

```
AUDIO FILE
    ↓
AUDIO PROCESSING (convert to WAV, metadata extraction)
    ↓
TRANSCRIPTION (faster-whisper large-v3 / medium with hallucination filtering)
    ↓
SPEAKER MATCHING (Zoom timeline JSON → speaker intervals → segment speaker labels)
    ↓
HINDI TO ENGLISH TRANSLATION (Ollama)
    ↓
INTERACTION ANALYSIS (Ollama + translated transcript)
    ↓
COMMUNICATION QUALITY ANALYSIS (Ollama + translated transcript)
    ↓
STUDENT PERFORMANCE ANALYSIS (Ollama + translated transcript)
    ↓
COMMUNICATION SENTIMENT ANALYSIS (librosa audio features + Ollama text classification)
    ↓
FINAL REPORT (Ollama + aggregated analysis JSONs)
    ↓
STRUCTURED JSON OUTPUT
```

### Not Implemented / Honest Gaps

| Feature | Status |
|---------|--------|
| Speaker diarization (audio-based) | NOT IMPLEMENTED — speaker labels come exclusively from Zoom timeline JSON |
| Timestamp generation | NOT IMPLEMENTED — timestamps come from Whisper segments and Zoom timeline |
| Audio format support beyond ffmpeg conversion | Partial — conversion to 16kHz mono WAV is handled via ffmpeg subprocess in test.py |
| Video analysis | Excluded per project rules; Duration_of_class.py is video-only and not integrated |
