"""
Flask Frontend Application for the Speech-to-Text API.
Serves a modern web UI and uses the shared transcription services.

Run with:
    python flask_app.py
"""

import os
import logging
import concurrent.futures
from pathlib import Path

from flask import Flask, render_template, request, jsonify

from core.config import settings
from core.exceptions import AudioProcessingError
from services.audio_validator import (
    cleanup_temp,
    save_to_temp,
    validate_audio_content,
    validate_extension,
    validate_size,
)
from services.transcriber import transcribe_audio, get_model, is_model_loaded

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(
    __name__,
    template_folder="templates",
    static_folder="static",
)
app.config["MAX_CONTENT_LENGTH"] = settings.MAX_FILE_SIZE_BYTES

# Thread pool for running CPU-heavy Whisper transcription without blocking Flask
_executor = concurrent.futures.ThreadPoolExecutor(max_workers=2)


# ─── Pre-load Model at Startup ────────────────────────────────────────────────

def _preload_whisper():
    """Download and load the Whisper model on startup so the first request is fast."""
    logger.info("Pre-loading Whisper model '%s' — this may take a moment on first run…", settings.WHISPER_MODEL)
    get_model()
    logger.info("Whisper model ready!")


# ─── Pages ─────────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    """Render the main transcription page."""
    return render_template(
        "index.html",
        supported_formats=", ".join(settings.SUPPORTED_EXTENSIONS),
        max_size_mb=settings.MAX_FILE_SIZE_BYTES // (1024 * 1024),
        whisper_model=settings.WHISPER_MODEL,
    )


# ─── API ───────────────────────────────────────────────────────────────────────

def _run_transcription(file_bytes: bytes, filename: str) -> dict:
    """
    Run the full validation → transcription pipeline.
    Designed to execute inside a thread pool so Flask stays responsive.
    """
    tmp_path = None
    try:
        ext = validate_extension(filename)
        validate_size(file_bytes)
        tmp_path = save_to_temp(file_bytes, suffix=ext)
        duration = validate_audio_content(tmp_path)
        result = transcribe_audio(tmp_path)
        return {
            "transcript": result["text"],
            "language": result.get("language"),
            "duration_seconds": round(duration, 3),
            "model_used": settings.WHISPER_MODEL,
        }
    finally:
        if tmp_path:
            cleanup_temp(tmp_path)


@app.route("/api/transcribe", methods=["POST"])
def api_transcribe():
    """Handle audio file upload and return transcript."""
    if "audio_file" not in request.files:
        return jsonify({"error": "NoFile", "detail": "No audio file provided.", "status_code": 400}), 400

    file = request.files["audio_file"]
    if file.filename == "":
        return jsonify({"error": "NoFile", "detail": "No file selected.", "status_code": 400}), 400

    try:
        # Read bytes on the main thread (fast I/O)
        file_bytes = file.read()
        filename = file.filename

        # Run heavy processing in thread pool so Flask doesn't block
        future = _executor.submit(_run_transcription, file_bytes, filename)
        result = future.result(timeout=300)  # 5-minute timeout

        return jsonify(result)

    except AudioProcessingError as exc:
        error_name = type(exc).__name__
        logger.warning("[%s] %s", error_name, exc.message)
        return jsonify({
            "error": error_name,
            "detail": exc.message,
            "status_code": exc.status_code,
        }), exc.status_code

    except concurrent.futures.TimeoutError:
        logger.error("Transcription timed out after 5 minutes.")
        return jsonify({
            "error": "TimeoutError",
            "detail": "Transcription took too long. Try a shorter audio file.",
            "status_code": 504,
        }), 504

    except Exception as exc:
        # Unwrap exceptions raised inside the thread pool
        if isinstance(exc, AudioProcessingError):
            error_name = type(exc).__name__
            return jsonify({"error": error_name, "detail": exc.message, "status_code": exc.status_code}), exc.status_code
        logger.exception("Unhandled error: %s", exc)
        return jsonify({
            "error": "InternalServerError",
            "detail": "An unexpected error occurred. Please try again.",
            "status_code": 500,
        }), 500


@app.route("/api/health")
def api_health():
    """Health check."""
    return jsonify({
        "status": "ok",
        "model_loaded": is_model_loaded(),
        "whisper_model": settings.WHISPER_MODEL,
        "version": settings.APP_VERSION,
    })


# ─── Run ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    # Pre-load model before starting the server
    _preload_whisper()
    app.run(host="0.0.0.0", port=5000, debug=False, threaded=True)
