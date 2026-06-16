"""
API routes for the Speech-to-Text API.
"""

import logging

from fastapi import APIRouter, File, UploadFile, HTTPException
from fastapi.responses import JSONResponse

from core.config import settings
from core.exceptions import AudioProcessingError
from schemas.models import ErrorResponse, HealthResponse, TranscriptResponse
from services.audio_validator import (
    cleanup_temp,
    save_to_temp,
    validate_audio_content,
    validate_extension,
    validate_size,
)
from services.transcriber import get_model, is_model_loaded, transcribe_audio

logger = logging.getLogger(__name__)
router = APIRouter()


# ─── Health Check ──────────────────────────────────────────────────────────────

@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Health Check",
    description="Returns the current health status of the API and whether the Whisper model is loaded.",
    tags=["Health"],
)
async def health_check() -> HealthResponse:
    return HealthResponse(
        status="ok",
        model_loaded=is_model_loaded(),
        whisper_model=settings.WHISPER_MODEL,
        version=settings.APP_VERSION,
    )


# ─── Transcription Endpoint ────────────────────────────────────────────────────

@router.post(
    "/transcribe",
    response_model=TranscriptResponse,
    responses={
        200: {"description": "Successful transcription.", "model": TranscriptResponse},
        413: {"description": "File too large.", "model": ErrorResponse},
        415: {"description": "Unsupported audio format.", "model": ErrorResponse},
        422: {"description": "Corrupted or empty audio file.", "model": ErrorResponse},
        500: {"description": "Internal server / transcription error.", "model": ErrorResponse},
    },
    summary="Transcribe Audio",
    description=(
        "Upload an audio file (WAV, MP3, MP4, OGG, FLAC, WEBM, AAC, AIFF, M4A) "
        "and receive the transcribed text powered by OpenAI Whisper."
    ),
    tags=["Transcription"],
)
async def transcribe(
    audio_file: UploadFile = File(
        ...,
        description="The audio file to transcribe. Supported formats: WAV, MP3, MP4, M4A, OGG, FLAC, WEBM, AAC, AIFF.",
    ),
) -> TranscriptResponse:
    """
    ## Endpoint: POST /api/v1/transcribe

    **Input**: Multipart form-data with an `audio_file` field.

    **Output**:
    ```json
    {
      "transcript": "REST APIs are stateless.",
      "language": "en",
      "duration_seconds": 3.52,
      "model_used": "base"
    }
    ```

    ### Error Handling
    | Condition           | HTTP Status | Error Type           |
    |---------------------|-------------|----------------------|
    | Unsupported format  | 415         | UnsupportedFormat    |
    | File too large      | 413         | FileTooLarge         |
    | Corrupted file      | 422         | CorruptedFile        |
    | Empty/silent audio  | 422         | EmptyAudio           |
    | Transcription error | 500         | TranscriptionError   |
    """
    filename = audio_file.filename or "upload"
    logger.info("Received upload: '%s' (content-type: %s)", filename, audio_file.content_type)

    tmp_path: str | None = None

    try:
        # ── 1. Validate file extension ──────────────────────────────────────
        ext = validate_extension(filename)

        # ── 2. Read file bytes ──────────────────────────────────────────────
        file_bytes = await audio_file.read()

        # ── 3. Validate file size ───────────────────────────────────────────
        validate_size(file_bytes)

        # ── 4. Persist to temp file ─────────────────────────────────────────
        tmp_path = save_to_temp(file_bytes, suffix=ext)
        logger.debug("Saved temporary file: %s", tmp_path)

        # ── 5. Validate audio content (corruption & emptiness) ──────────────
        duration = validate_audio_content(tmp_path)
        logger.info("Audio validated — duration: %.2f s", duration)

        # ── 6. Transcribe ───────────────────────────────────────────────────
        result = transcribe_audio(tmp_path)

        return TranscriptResponse(
            transcript=result["text"],
            language=result.get("language"),
            duration_seconds=round(duration, 3),
            model_used=settings.WHISPER_MODEL,
        )

    except AudioProcessingError as exc:
        # Known, structured errors → return as JSON error body
        error_name = type(exc).__name__
        logger.warning("[%s] %s", error_name, exc.message)
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": error_name,
                "detail": exc.message,
                "status_code": exc.status_code,
            },
        )

    except Exception as exc:
        # Unexpected errors
        logger.exception("Unhandled exception during transcription: %s", exc)
        return JSONResponse(
            status_code=500,
            content={
                "error": "InternalServerError",
                "detail": "An unexpected error occurred. Please try again.",
                "status_code": 500,
            },
        )

    finally:
        if tmp_path:
            cleanup_temp(tmp_path)
            logger.debug("Cleaned up temp file: %s", tmp_path)
