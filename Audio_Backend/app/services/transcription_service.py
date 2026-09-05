import os
import sys
import logging
import uuid
from pathlib import Path
from typing import Optional, Dict, Any, List

# Ensure existing code is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from app.existing_code.test import (
    convert_to_wav,
    load_zoom_timeline,
    match_with_speakers,
    process_and_clean_segments,
    save_transcription,
    transcribe_with_faster_whisper_large,
    detect_hallucination,
)
from app.tools.audio_processor import convert_to_wav as tool_convert_to_wav, cleanup_temp_file
from app.tools.metadata import extract_audio_metadata, validate_audio_file

logger = logging.getLogger(__name__)


class TranscriptionService:
    def __init__(self, upload_dir: str, output_dir: str):
        self.upload_dir = upload_dir
        self.output_dir = output_dir
        os.makedirs(upload_dir, exist_ok=True)
        os.makedirs(output_dir, exist_ok=True)

    def transcribe(self, audio_file_path: str, timeline_json_path: Optional[str] = None) -> Dict[str, Any]:
        logger.info(f"Starting transcription for: {audio_file_path}")
        is_valid, error = validate_audio_file(audio_file_path)
        if not is_valid:
            raise ValueError(error)

        metadata = extract_audio_metadata(audio_file_path)
        wav_path = tool_convert_to_wav(audio_file_path, self.upload_dir)
        if not wav_path:
            raise RuntimeError("Audio conversion to WAV failed")

        try:
            timeline = None
            if timeline_json_path and os.path.exists(timeline_json_path):
                timeline = load_zoom_timeline(timeline_json_path)
                logger.info(f"Loaded Zoom timeline with {len(timeline)} entries")

            segments, info = transcribe_with_faster_whisper_large(wav_path)
            if not segments:
                raise RuntimeError("No valid transcription segments generated")

            matched_segments, speaker_segments = match_with_speakers(segments, timeline)
            cleaned_segments = process_and_clean_segments(matched_segments)

            transcript_path = save_transcription(cleaned_segments, wav_path, info)

            speakers = []
            for speaker_name, spk_segments in speaker_segments.items():
                speakers.append({
                    "name": speaker_name,
                    "segment_count": len(spk_segments),
                    "total_duration": sum(s["end"] - s["start"] for s in spk_segments),
                })

            result = {
                "segments": cleaned_segments,
                "speakers": speakers,
                "duration": metadata.get("duration"),
                "language": "hi",
                "model_used": "large-v3",
                "transcript_path": transcript_path,
            }
            logger.info(f"Transcription completed: {len(cleaned_segments)} segments, {len(speakers)} speakers")
            return result
        finally:
            if wav_path != audio_file_path:
                cleanup_temp_file(wav_path)

    def transcribe_simple(self, audio_file_path: str) -> Dict[str, Any]:
        is_valid, error = validate_audio_file(audio_file_path)
        if not is_valid:
            raise ValueError(error)

        metadata = extract_audio_metadata(audio_file_path)
        wav_path = tool_convert_to_wav(audio_file_path, self.upload_dir)
        if not wav_path:
            raise RuntimeError("Audio conversion to WAV failed")

        try:
            segments, info = transcribe_with_faster_whisper_large(wav_path)
            if not segments:
                raise RuntimeError("No valid transcription segments generated")

            cleaned_segments = process_and_clean_segments(segments)
            for seg in cleaned_segments:
                seg["speaker"] = "Unknown"

            result = {
                "segments": cleaned_segments,
                "speakers": [{"name": "Unknown", "segment_count": len(cleaned_segments), "total_duration": sum(s["end"] - s["start"] for s in cleaned_segments)}],
                "duration": metadata.get("duration"),
                "language": "hi",
                "model_used": "large-v3",
            }
            return result
        finally:
            if wav_path != audio_file_path:
                cleanup_temp_file(wav_path)
