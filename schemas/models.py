"""
Pydantic schemas for request/response models.
"""

from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


# ─── Response Models ───────────────────────────────────────────────────────────

class TranscriptResponse(BaseModel):
    """Successful transcription response."""
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "transcript": "REST APIs are stateless.",
                "language": "en",
                "duration_seconds": 3.52,
                "model_used": "base",
            }
        }
    )

    transcript: str = Field(
        ...,
        description="The transcribed text extracted from the audio file.",
    )
    language: Optional[str] = Field(
        None,
        description="Detected language of the audio (ISO 639-1 code).",
    )
    duration_seconds: Optional[float] = Field(
        None,
        description="Duration of the audio file in seconds.",
    )
    model_used: str = Field(
        ...,
        description="Whisper model version used for transcription.",
    )


class ErrorResponse(BaseModel):
    """Standard error response."""
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "error": "UnsupportedFormat",
                "detail": "Unsupported audio format: '.xyz'",
                "status_code": 415,
            }
        }
    )

    error: str = Field(..., description="Error type or category.")
    detail: str = Field(..., description="Human-readable error description.")
    status_code: int = Field(..., description="HTTP status code.")


class HealthResponse(BaseModel):
    """Health check response."""
    status: str = Field(..., description="API status (ok).")
    model_loaded: bool = Field(..., description="Whether the Whisper model is loaded.")
    whisper_model: str = Field(..., description="Active Whisper model name.")
    version: str = Field(..., description="API version.")
