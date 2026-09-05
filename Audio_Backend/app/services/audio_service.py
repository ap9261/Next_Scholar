import os
import sys
import logging
import uuid
from typing import Optional, Dict, Any

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from app.db.crud.audio import create_audio, get_audio, update_audio
from app.db.crud.transcript import create_transcript, create_transcript_segment
from app.db.crud.analysis import create_analysis_result, create_analysis_job, update_analysis_job
from app.db.models import AudioFile
from app.services.transcription_service import TranscriptionService
from app.services.analysis_service import AnalysisService
from app.tools.audio_processor import ensure_wav
from app.tools.metadata import extract_audio_metadata, validate_audio_file

logger = logging.getLogger(__name__)


class AudioService:
    def __init__(self, upload_dir: str, output_dir: str, ollama_model: str, ollama_base_url: str):
        self.upload_dir = upload_dir
        self.output_dir = output_dir
        self.transcription_service = TranscriptionService(upload_dir, output_dir)
        self.analysis_service = AnalysisService(output_dir, ollama_model, ollama_base_url)

    def process_audio(self, db, audio_file_path: str, original_filename: str, timeline_json_path: Optional[str] = None) -> Dict[str, Any]:
        audio_id = str(uuid.uuid4())
        is_valid, error = validate_audio_file(audio_file_path)
        if not is_valid:
            raise ValueError(error)

        metadata = extract_audio_metadata(audio_file_path)
        db_audio = create_audio(
            db,
            audio={
                "filename": original_filename,
                "file_path": audio_file_path,
                "file_size": os.path.getsize(audio_file_path),
                "duration": metadata.get("duration"),
                "format": metadata.get("format"),
                "sample_rate": metadata.get("sample_rate"),
                "channels": metadata.get("channels"),
            },
        )
        db_job = create_analysis_job(db, {"audio_id": db_audio.id, "status": "processing", "current_stage": "transcription", "progress": 0.0})

        try:
            update_analysis_job(db, db_job.id, progress=10.0, current_stage="transcription")
            transcription_result = self.transcription_service.transcribe(audio_file_path, timeline_json_path)
            update_analysis_job(db, db_job.id, progress=30.0, current_stage="translation")

            db_transcript = create_transcript(
                db,
                {
                    "audio_id": db_audio.id,
                    "text": " ".join(seg.get("text", "") for seg in transcription_result.get("segments", [])),
                    "segments": transcription_result.get("segments", []),
                    "language": transcription_result.get("language"),
                    "model_used": transcription_result.get("model_used"),
                    "duration": transcription_result.get("duration"),
                },
            )
            for idx, seg in enumerate(transcription_result.get("segments", [])):
                create_transcript_segment(
                    db,
                    {
                        "start": seg.get("start", 0),
                        "end": seg.get("end", 0),
                        "text": seg.get("text", ""),
                        "speaker": seg.get("speaker"),
                        "segment_index": idx,
                    },
                    db_transcript.id,
                )

            translated = self.analysis_service.translate_hindi_to_english(transcription_result)
            update_analysis_job(db, db_job.id, progress=50.0, current_stage="interaction_analysis")

            interaction = self.analysis_service.analyze_interactions(translated)
            create_analysis_result(
                db,
                {
                    "audio_id": db_audio.id,
                    "analysis_type": "interaction",
                    "result_data": interaction,
                    "status": "completed" if "error" not in interaction else "failed",
                    "error_message": interaction.get("error"),
                },
            )
            update_analysis_job(db, db_job.id, progress=65.0, current_stage="communication_quality")

            quality = self.analysis_service.analyze_communication_quality(translated)
            create_analysis_result(
                db,
                {
                    "audio_id": db_audio.id,
                    "analysis_type": "communication_quality",
                    "result_data": quality,
                    "status": "completed" if "error" not in quality else "failed",
                    "error_message": quality.get("error"),
                },
            )
            update_analysis_job(db, db_job.id, progress=80.0, current_stage="student_performance")

            performance = self.analysis_service.analyze_student_performance(translated)
            create_analysis_result(
                db,
                {
                    "audio_id": db_audio.id,
                    "analysis_type": "student_performance",
                    "result_data": performance,
                    "status": "completed" if "error" not in performance else "failed",
                    "error_message": performance.get("error"),
                },
            )
            update_analysis_job(db, db_job.id, progress=90.0, current_stage="communication_sentiment")

            sentiment = self.analysis_service.analyze_communication_sentiment(translated, audio_file_path)
            create_analysis_result(
                db,
                {
                    "audio_id": db_audio.id,
                    "analysis_type": "communication_sentiment",
                    "result_data": sentiment,
                    "status": "completed" if "error" not in sentiment else "failed",
                    "error_message": sentiment.get("error"),
                },
            )
            update_analysis_job(db, db_job.id, progress=95.0, current_stage="final_report")

            final_report = self.analysis_service.generate_final_report({
                "interaction": interaction,
                "communication_quality": quality,
                "student_performance": performance,
                "communication_sentiment": sentiment,
                "translated_conversation": translated,
            })
            create_analysis_result(
                db,
                {
                    "audio_id": db_audio.id,
                    "analysis_type": "final_report",
                    "result_data": final_report,
                    "report_text": final_report.get("report_text"),
                    "status": "completed" if "error" not in final_report else "failed",
                    "error_message": final_report.get("error"),
                },
            )

            update_audio(db, db_audio.id, {"status": "completed"})
            update_analysis_job(db, db_job.id, status="completed", progress=100.0, current_stage="completed", result={"audio_id": db_audio.id})

            logger.info(f"Audio processing completed for {audio_id}")
            return {
                "job_id": db_job.id,
                "audio_id": db_audio.id,
                "status": "completed",
                "transcript": transcription_result,
                "translation": translated,
            }
        except Exception as e:
            logger.error(f"Audio processing failed for {audio_id}: {e}")
            update_audio(db, db_audio.id, {"status": "failed", "error_message": str(e)})
            update_analysis_job(db, db_job.id, status="failed", error_message=str(e))
            raise
