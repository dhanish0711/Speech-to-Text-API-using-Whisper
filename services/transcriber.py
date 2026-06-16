"""
Whisper transcription service.
Handles model loading (singleton) and audio transcription.
"""

import os
import logging
from pathlib import Path
from typing import Optional

# ─── Ensure ffmpeg is on PATH (required by Whisper on Windows) ─────────────────
# Whisper calls `ffmpeg` via subprocess. The imageio-ffmpeg package bundles an
# ffmpeg binary but names it differently (e.g. ffmpeg-win-x86_64-v7.1.exe).
# We copy it as `ffmpeg.exe` into a local bin/ folder and add that to PATH.
import shutil as _shutil

def _setup_ffmpeg():
    """Make ffmpeg available to Whisper on Windows."""
    # Already available system-wide?
    if _shutil.which("ffmpeg"):
        return

    try:
        import imageio_ffmpeg
        src = imageio_ffmpeg.get_ffmpeg_exe()
        bin_dir = Path(__file__).resolve().parent.parent / "bin"
        bin_dir.mkdir(exist_ok=True)
        dst = bin_dir / "ffmpeg.exe"
        if not dst.exists():
            _shutil.copy2(src, dst)
            logging.getLogger(__name__).info("Copied ffmpeg to %s", dst)
        os.environ["PATH"] = str(bin_dir) + os.pathsep + os.environ.get("PATH", "")
        logging.getLogger(__name__).info("Added ffmpeg to PATH from %s", bin_dir)
    except ImportError:
        logging.getLogger(__name__).warning(
            "ffmpeg not found. Install it system-wide or run: pip install imageio-ffmpeg"
        )

_setup_ffmpeg()

import whisper

from core.config import settings
from core.exceptions import TranscriptionError

logger = logging.getLogger(__name__)

# ─── Singleton model instance ──────────────────────────────────────────────────
_whisper_model: Optional[whisper.Whisper] = None


def get_model() -> whisper.Whisper:
    """
    Return the loaded Whisper model, loading it on first call (lazy singleton).
    Thread-safe for read operations after the first load.
    """
    global _whisper_model
    if _whisper_model is None:
        logger.info("Loading Whisper model '%s' …", settings.WHISPER_MODEL)
        try:
            _whisper_model = whisper.load_model(settings.WHISPER_MODEL)
            logger.info("Whisper model '%s' loaded successfully.", settings.WHISPER_MODEL)
        except Exception as exc:
            logger.error("Failed to load Whisper model: %s", exc)
            raise TranscriptionError(f"Failed to load Whisper model: {exc}") from exc
    return _whisper_model


def is_model_loaded() -> bool:
    """Return True if the model has already been initialised."""
    return _whisper_model is not None


def transcribe_audio(file_path: str) -> dict:
    """
    Run Whisper on a local audio file and return the result dict.

    Parameters
    ----------
    file_path : str
        Absolute path to the (already-validated) temporary audio file.

    Returns
    -------
    dict with keys:
        - text (str)        : full transcript
        - language (str)    : detected ISO 639-1 language code
        - segments (list)   : segment-level details

    Raises
    ------
    TranscriptionError  : on any Whisper failure.
    """
    model = get_model()
    try:
        logger.info("Starting transcription for '%s'", file_path)
        result = model.transcribe(
            file_path,
            fp16=False,          # safer across CPU-only environments
            verbose=False,
        )
        transcript = result.get("text", "").strip()
        language = result.get("language", None)
        logger.info("Transcription complete. Language: %s, Length: %d chars", language, len(transcript))
        return {
            "text": transcript,
            "language": language,
            "segments": result.get("segments", []),
        }
    except Exception as exc:
        logger.error("Whisper transcription error: %s", exc)
        raise TranscriptionError(str(exc)) from exc
