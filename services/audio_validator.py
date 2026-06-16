"""
Audio validation service.
Validates uploaded audio files before transcription:
  - Extension / MIME type check
  - File size check
  - Corruption / readability check
  - Empty or near-silent audio check
"""

import os
import logging
import tempfile
from pathlib import Path

import soundfile as sf
import numpy as np

from core.config import settings
from core.exceptions import (
    CorruptedFileError,
    EmptyAudioError,
    FileTooLargeError,
    UnsupportedFormatError,
)

logger = logging.getLogger(__name__)


def validate_extension(filename: str) -> str:
    """
    Return the file extension (lower-case) or raise UnsupportedFormatError.
    """
    ext = Path(filename).suffix.lower()
    if ext not in settings.SUPPORTED_EXTENSIONS:
        raise UnsupportedFormatError(extension=ext)
    return ext


def validate_size(file_bytes: bytes) -> None:
    """Raise FileTooLargeError if the file exceeds the configured limit."""
    size = len(file_bytes)
    if size > settings.MAX_FILE_SIZE_BYTES:
        max_mb = settings.MAX_FILE_SIZE_BYTES // (1024 * 1024)
        raise FileTooLargeError(max_mb=max_mb)


def validate_audio_content(file_path: str) -> float:
    """
    Validate that the audio file is:
      1. Readable (not corrupted).
      2. Contains audible content (not empty/silent).

    Returns the duration in seconds.
    """
    try:
        with sf.SoundFile(file_path) as audio_file:
            frames = audio_file.frames
            sample_rate = audio_file.samplerate

            if frames == 0 or sample_rate == 0:
                raise EmptyAudioError()

            duration = frames / sample_rate

            if duration < settings.MIN_AUDIO_DURATION_SECONDS:
                raise EmptyAudioError()

            # Read all audio data and check for near-silence
            audio_data = audio_file.read(dtype="float32")
            rms = float(np.sqrt(np.mean(audio_data ** 2)))
            logger.debug("Audio RMS amplitude: %.6f", rms)

            # Threshold for "empty" audio (no audible signal)
            if rms < 1e-6:
                raise EmptyAudioError()

            return duration

    except EmptyAudioError:
        raise
    except sf.LibsndfileError as exc:
        logger.warning("soundfile error reading '%s': %s", file_path, exc)
        raise CorruptedFileError(detail=str(exc)) from exc
    except Exception as exc:
        logger.warning("Unexpected error validating audio '%s': %s", file_path, exc)
        raise CorruptedFileError(detail=str(exc)) from exc


def save_to_temp(file_bytes: bytes, suffix: str) -> str:
    """
    Write raw bytes to a named temporary file and return its path.
    The caller is responsible for deleting the file afterwards.
    """
    tmp = tempfile.NamedTemporaryFile(
        suffix=suffix, delete=False, dir=settings.TEMP_DIR
    )
    try:
        tmp.write(file_bytes)
        tmp.flush()
        return tmp.name
    finally:
        tmp.close()


def cleanup_temp(file_path: str) -> None:
    """Silently remove a temporary file."""
    try:
        os.unlink(file_path)
    except OSError:
        pass
