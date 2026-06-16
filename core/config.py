"""
Core configuration settings for the Speech-to-Text API.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # App metadata
    APP_NAME: str = "Speech-to-Text API"
    APP_DESCRIPTION: str = (
        "A production-ready REST API for audio transcription powered by OpenAI Whisper. "
        "Supports multiple audio formats and handles edge cases such as corrupted files, "
        "unsupported formats, and empty audio."
    )
    APP_VERSION: str = "1.0.0"

    # Whisper model configuration
    # Options: "tiny", "base", "small", "medium", "large", "large-v2", "large-v3"
    WHISPER_MODEL: str = "base"

    # Supported audio MIME types and extensions
    SUPPORTED_MIME_TYPES: list[str] = [
        "audio/wav",
        "audio/x-wav",
        "audio/mpeg",       # mp3
        "audio/mp3",
        "audio/mp4",
        "audio/x-m4a",
        "audio/ogg",
        "audio/flac",
        "audio/x-flac",
        "audio/webm",
        "audio/aac",
        "audio/aiff",
        "video/mp4",        # mp4 video with audio track
        "video/webm",
    ]

    SUPPORTED_EXTENSIONS: list[str] = [
        ".wav", ".mp3", ".mp4", ".m4a",
        ".ogg", ".flac", ".webm", ".aac",
        ".aiff", ".aif",
    ]

    # File size limit (in bytes) — default 100 MB
    MAX_FILE_SIZE_BYTES: int = 100 * 1024 * 1024

    # Minimum audio duration in seconds to consider non-empty
    MIN_AUDIO_DURATION_SECONDS: float = 0.1

    # Temporary file directory
    TEMP_DIR: str = "/tmp"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
    )


settings = Settings()
