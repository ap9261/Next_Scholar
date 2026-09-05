import os
import sys
import logging
import importlib.util
from typing import Optional, Dict, Any, List
from pathlib import Path

logger = logging.getLogger(__name__)


def load_existing_module(module_name: str, file_path: str):
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


class AnalysisService:
    def __init__(self, output_dir: str, ollama_model: str, ollama_base_url: str):
        self.output_dir = output_dir
        self.ollama_model = ollama_model
        self.ollama_base_url = ollama_base_url
        os.makedirs(output_dir, exist_ok=True)
        self._modules = {}

    def _get_module(self, module_name: str, relative_path: str):
        if module_name not in self._modules:
            base_dir = os.path.join(os.path.dirname(__file__), "..", "existing_code")
            file_path = os.path.join(base_dir, relative_path)
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"Existing module not found: {file_path}")
            self._modules[module_name] = load_existing_module(module_name, file_path)
        return self._modules[module_name]

    def translate_hindi_to_english(self, transcript_data: Dict[str, Any]) -> Dict[str, Any]:
        logger.info("Starting Hindi to English translation")
        module = self._get_module("hindi_to_english", "hindi_to_english.py")
        segments = transcript_data.get("segments", [])
        translated = []
        filtered_disturbance = 0
        filtered_invalid = 0
        filtered_short = 0
        translation_errors = 0
        for seg in segments:
            text = seg.get("text", "")
            speaker = seg.get("speaker", "Unknown")
            start = seg.get("start", 0)
            hindi_text = seg.get("hindi", text)
            if not hindi_text or len(hindi_text.strip()) < 4:
                filtered_short += 1
                continue
            if hasattr(module, "is_disturbance_text") and module.is_disturbance_text(hindi_text):
                filtered_disturbance += 1
                continue
            if hasattr(module, "is_valid_hindi_text") and not module.is_valid_hindi_text(hindi_text):
                filtered_invalid += 1
                continue
            english = module.translate_to_english(hindi_text)
            if english:
                translated.append({
                    "time": module.format_time(start),
                    "time_seconds": start,
                    "speaker": speaker,
                    "hindi": hindi_text,
                    "english": english,
                })
            else:
                translation_errors += 1
        translated.sort(key=lambda x: x["time_seconds"])
        result = {
            "translations": translated,
            "metadata": {
                "total_sentences": len(translated),
                "model": self.ollama_model,
                "filtered_disturbance": filtered_disturbance,
                "filtered_invalid": filtered_invalid,
                "filtered_short": filtered_short,
                "translation_errors": translation_errors,
            },
        }
        logger.info(f"Translation completed: {len(translated)} sentences")
        return result

    def analyze_interactions(self, translated_data: Dict[str, Any]) -> Dict[str, Any]:
        logger.info("Starting interaction analysis")
        module = self._get_module("respond", "respond.py")
        segments = self._build_segments_from_translations(translated_data)
        json_file = os.path.join(self.output_dir, "translated_conversation.json")
        with open(json_file, "w", encoding="utf-8") as f:
            import json
            json.dump({"translations": translated_data.get("translations", [])}, f, ensure_ascii=False)

        original_model = getattr(module, "MODEL_NAME", None)
        module.MODEL_NAME = self.ollama_model
        try:
            interaction_data = module.analyze_interactions(segments, self._extract_teacher_name(segments))
            if original_model:
                module.MODEL_NAME = original_model
            if not interaction_data:
                return {}
            report_lines = module.generate_interaction_report(interaction_data, self._extract_teacher_name(segments), json_file)
            output_json = os.path.join(self.output_dir, "interaction_analysis_report.json")
            module.save_json_output(interaction_data, self._extract_teacher_name(segments), json_file)
            logger.info("Interaction analysis completed")
            return {
                "summary": interaction_data.get("summary", {}),
                "unresponded": interaction_data.get("unresponded", {}),
                "students": interaction_data.get("student_summary", {}),
                "report_text": "\n".join(report_lines),
            }
        except Exception as e:
            logger.error(f"Interaction analysis failed: {e}")
            return {"error": str(e)}

    def analyze_communication_quality(self, translated_data: Dict[str, Any]) -> Dict[str, Any]:
        logger.info("Starting communication quality analysis")
        module = self._get_module("respond_detail", "respond_detail.py")
        segments = self._build_segments_from_translations(translated_data)
        original_model = getattr(module, "MODEL_NAME", None)
        module.MODEL_NAME = self.ollama_model
        try:
            interactions = module.analyze_communication_quality(segments, self._extract_teacher_name(segments))
            if original_model:
                module.MODEL_NAME = original_model
            if not interactions or not interactions.get("all_interactions"):
                return {}
            report_lines = module.generate_quality_report(interactions, self._extract_teacher_name(segments), "translated_conversation.json")
            logger.info("Communication quality analysis completed")
            return {
                "summary": interactions.get("summary_stats", {}),
                "all_interactions": interactions.get("all_interactions", []),
                "report_text": "\n".join(report_lines),
            }
        except Exception as e:
            logger.error(f"Communication quality analysis failed: {e}")
            return {"error": str(e)}

    def analyze_student_performance(self, translated_data: Dict[str, Any]) -> Dict[str, Any]:
        logger.info("Starting student performance analysis")
        module = self._get_module("extra_task", "extra_task.py")
        segments = self._build_segments_from_translations(translated_data)
        original_model = getattr(module, "MODEL_NAME", None)
        module.MODEL_NAME = self.ollama_model
        try:
            analysis_data = module.analyze_student_performance(segments, self._extract_teacher_name(segments))
            if original_model:
                module.MODEL_NAME = original_model
            if not analysis_data:
                return {}
            report_lines = module.generate_performance_report(analysis_data, self._extract_teacher_name(segments), "translated_conversation.json")
            logger.info("Student performance analysis completed")
            return {
                "summary": analysis_data.get("summary", {}),
                "student_classifications": {
                    name: {
                        "classification": data.get("classification", {}),
                        "metrics": {
                            "score": data.get("classification", {}).get("score", 0),
                            "accuracy": data.get("classification", {}).get("accuracy", 0),
                            "quality_ratio": data.get("classification", {}).get("quality_ratio", 0),
                            "questions_asked": data.get("classification", {}).get("questions_asked", 0),
                        },
                    }
                    for name, data in analysis_data.get("student_classifications", {}).items()
                },
                "report_text": "\n".join(report_lines),
            }
        except Exception as e:
            logger.error(f"Student performance analysis failed: {e}")
            return {"error": str(e)}

    def analyze_communication_sentiment(self, translated_data: Dict[str, Any], audio_file_path: str) -> Dict[str, Any]:
        logger.info("Starting communication sentiment analysis")
        module = self._get_module("Type_of_conversation", "Type_of_conversation.py")
        segments = self._build_segments_from_translations(translated_data)
        original_model = getattr(module, "MODEL_NAME", None)
        module.MODEL_NAME = self.ollama_model
        try:
            pitch_data = None
            if os.path.exists(audio_file_path):
                pitch_data = module.extract_pitch_features(audio_file_path)
            teacher_name = self._extract_teacher_name(segments)
            classifications = module.classify_communication(segments, teacher_name, pitch_data)
            if not classifications or not classifications.get("all_segments"):
                return {}
            analysis = module.analyze_sentiment_patterns(classifications)
            report_lines = module.generate_systematic_report(classifications, analysis, teacher_name, "translated_conversation.json")
            logger.info("Communication sentiment analysis completed")
            return {
                "overall": analysis.get("overall", {}),
                "teacher": {
                    "total": analysis.get("teacher", {}).get("total", 0),
                    "positive": len(analysis.get("teacher", {}).get("positive", [])),
                    "negative": len(analysis.get("teacher", {}).get("negative", [])),
                    "neutral": len(analysis.get("teacher", {}).get("neutral", [])),
                },
                "students": {
                    name: {
                        "total": data.get("total", 0),
                        "positive": len(data.get("positive", [])),
                        "negative": len(data.get("negative", [])),
                        "neutral": len(data.get("neutral", [])),
                    }
                    for name, data in analysis.get("students", {}).items()
                },
                "audio_analysis_summary": analysis.get("audio_analysis_summary", {}),
                "report_text": "\n".join(report_lines),
            }
        except Exception as e:
            logger.error(f"Communication sentiment analysis failed: {e}")
            return {"error": str(e)}
        finally:
            if original_model:
                module.MODEL_NAME = original_model

    def generate_final_report(self, all_analysis_data: Dict[str, Any]) -> Dict[str, Any]:
        logger.info("Generating final report")
        module = self._get_module("final_report", "final_report.py")
        original_model = getattr(module, "MODEL_NAME", None)
        module.MODEL_NAME = self.ollama_model
        try:
            module.FILES = {
                "interaction_report": os.path.join(self.output_dir, "interaction_analysis_report.json"),
                "communication_quality": os.path.join(self.output_dir, "communication_quality_report.json"),
                "student_performance": os.path.join(self.output_dir, "student_performance_analysis_report.json"),
                "translated_conversation": os.path.join(self.output_dir, "translated_conversation.json"),
                "communication_sentiment": os.path.join(self.output_dir, "communication_sentiment.json"),
            }
            all_data = module.load_all_analyses()
            analysis_text = module.generate_comprehensive_analysis(all_data)
            if not analysis_text:
                return {"error": "Failed to generate comprehensive analysis"}
            report_lines = module.generate_final_report(analysis_text, all_data)
            json_output = {
                "metadata": {"generated": __import__("datetime").datetime.now().isoformat(), "type": "Final Conclusion Report"},
                "conclusion": analysis_text,
            }
            logger.info("Final report generated")
            return {
                "conclusion": analysis_text,
                "report_text": "\n".join(report_lines),
                "json_output": json_output,
            }
        except Exception as e:
            logger.error(f"Final report generation failed: {e}")
            return {"error": str(e)}
        finally:
            if original_model:
                module.MODEL_NAME = original_model

    def _build_segments_from_translations(self, translated_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        segments = []
        for item in translated_data.get("translations", []):
            segments.append({
                "speaker": item.get("speaker", "Unknown"),
                "text": item.get("english", item.get("hindi", "")),
                "hindi": item.get("hindi", ""),
                "start": item.get("time_seconds", 0),
                "end": item.get("time_seconds", 0) + 2,
                "time": item.get("time", "00:00"),
            })
        return segments

    def _extract_teacher_name(self, segments: List[Dict[str, Any]]) -> str:
        speakers = set(seg.get("speaker", "Unknown") for seg in segments)
        for name in ["Danish", "Danish Hayat", "Teacher", "Sir", "Madam", "Mam", "Hayat"]:
            for speaker in speakers:
                if name.lower() in speaker.lower():
                    return speaker
        counts = {}
        for seg in segments:
            sp = seg.get("speaker", "Unknown")
            counts[sp] = counts.get(sp, 0) + 1
        if counts:
            return max(counts, key=counts.get)
        return "Teacher"
