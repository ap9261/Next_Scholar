import logging
from typing import Optional, Dict, Any

from app.db.crud.analysis import create_analysis_result, get_analysis_result_by_type
from app.db.session import SessionLocal

logger = logging.getLogger(__name__)


class ReportService:
    def __init__(self, output_dir: str):
        self.output_dir = output_dir

    def save_report(self, audio_id: str, analysis_type: str, report_text: str, result_data: Optional[Dict[str, Any]] = None) -> None:
        db = SessionLocal()
        try:
            existing = get_analysis_result_by_type(db, audio_id, analysis_type)
            if existing:
                existing.report_text = report_text
                if result_data:
                    existing.result_data = result_data
                existing.status = "completed"
                db.commit()
            else:
                create_analysis_result(
                    db,
                    {
                        "audio_id": audio_id,
                        "analysis_type": analysis_type,
                        "report_text": report_text,
                        "result_data": result_data,
                        "status": "completed",
                    },
                )
            logger.info(f"Report saved for {audio_id} / {analysis_type}")
        finally:
            db.close()

    def get_report(self, audio_id: str, analysis_type: str) -> Optional[Dict[str, Any]]:
        db = SessionLocal()
        try:
            result = get_analysis_result_by_type(db, audio_id, analysis_type)
            if not result:
                return None
            return {
                "id": result.id,
                "analysis_type": result.analysis_type,
                "status": result.status,
                "report_text": result.report_text,
                "result_data": result.result_data,
                "created_at": result.created_at.isoformat() if result.created_at else None,
            }
        finally:
            db.close()
