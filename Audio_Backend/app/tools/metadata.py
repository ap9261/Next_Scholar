import os
import logging
import subprocess
from typing import Optional, Tuple
import soundfile as sf

logger = logging.getLogger(__name__)


def _probe_with_ffprobe(audio_file: str) -> dict:
    try:
        cmd = [
            "ffprobe",
            "-v", "error",
            "-show_format",
            "-show_streams",
            audio_file,
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        info = {"format": None, "duration": None, "sample_rate": None, "channels": None}
        for line in result.stdout.splitlines():
            line = line.strip()
            if line.startswith("format_name="):
                info["format"] = line.split("=", 1)[1]
            elif line.startswith("duration="):
                try:
                    info["duration"] = float(line.split("=", 1)[1])
                except ValueError:
                    pass
            elif line.startswith("sample_rate="):
                try:
                    info["sample_rate"] = int(line.split("=", 1)[1])
                except ValueError:
                    pass
            elif line.startswith("channels="):
                try:
                    info["channels"] = int(line.split("=", 1)[1])
                except ValueError:
                    pass
        return {k: v for k, v in info.items() if v is not None}
    except Exception as e:
        logger.debug(f"ffprobe fallback failed: {e}")
        return {}


def extract_audio_metadata(audio_file: str) -> dict:
    try:
        info = sf.info(audio_file)
        return {
            "duration": float(info.duration),
            "sample_rate": int(info.samplerate),
            "channels": int(info.channels),
            "format": info.format,
            "subtype": info.subtype if hasattr(info, "subtype") else None,
        }
    except Exception as e_sf:
        logger.debug(f"soundfile metadata extraction failed, trying ffprobe: {e_sf}")
        ffprobe_info = _probe_with_ffprobe(audio_file)
        if ffprobe_info:
            return ffprobe_info
        logger.error(f"Failed to extract metadata from {audio_file}: {e_sf}")
        return {}


def get_audio_duration(audio_file: str) -> Optional[float]:
    try:
        info = sf.info(audio_file)
        return float(info.duration)
    except Exception as e_sf:
        logger.debug(f"soundfile duration failed, trying ffprobe: {e_sf}")
        ffprobe_info = _probe_with_ffprobe(audio_file)
        if "duration" in ffprobe_info:
            return float(ffprobe_info["duration"])
        logger.error(f"Failed to get duration for {audio_file}: {e_sf}")
        return None


def validate_audio_file(audio_file: str) -> Tuple[bool, Optional[str]]:
    if not os.path.exists(audio_file):
        return False, f"File not found: {audio_file}"
    try:
        sf.info(audio_file)
        return True, None
    except Exception as e_sf:
        ffprobe_info = _probe_with_ffprobe(audio_file)
        if ffprobe_info.get("duration") and ffprobe_info.get("sample_rate"):
            return True, None
        return False, f"Invalid audio file: {e_sf}"

