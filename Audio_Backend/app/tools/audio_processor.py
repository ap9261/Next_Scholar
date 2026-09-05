import os
import subprocess
import logging
from typing import Optional, Tuple
from pathlib import Path

logger = logging.getLogger(__name__)


def check_ffmpeg() -> bool:
    try:
        subprocess.run(["ffmpeg", "-version"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
        return True
    except FileNotFoundError:
        return False


def convert_to_wav(audio_file: str, output_dir: Optional[str] = None) -> Optional[str]:
    if not check_ffmpeg():
        logger.warning("FFmpeg not found. Skipping conversion.")
        return audio_file

    base_name = Path(audio_file).stem
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
        output_file = os.path.join(output_dir, f"{base_name}.wav")
    else:
        output_file = f"{base_name}.wav"

    if os.path.exists(output_file):
        logger.info(f"Using existing WAV file: {output_file}")
        return output_file

    logger.info(f"Converting audio to WAV: {audio_file}")
    try:
        subprocess.run(
            ["ffmpeg", "-i", audio_file, "-ar", "16000", "-ac", "1", "-y", output_file],
            check=True,
            capture_output=True,
            text=True,
        )
        logger.info(f"Converted to: {output_file}")
        return output_file
    except subprocess.CalledProcessError as e:
        logger.error(f"Audio conversion failed: {e.stderr}")
        return None


def ensure_wav(audio_file: str, output_dir: Optional[str] = None) -> str:
    suffix = Path(audio_file).suffix.lower()
    if suffix in (".wav",):
        return audio_file
    return convert_to_wav(audio_file, output_dir) or audio_file


def cleanup_temp_file(file_path: str) -> None:
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
            logger.info(f"Cleaned up temp file: {file_path}")
    except Exception as e:
        logger.warning(f"Failed to cleanup temp file {file_path}: {e}")
