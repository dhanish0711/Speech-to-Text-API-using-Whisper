"""
Custom exception classes for the Speech-to-Text API.
"""


class AudioProcessingError(Exception):
    """Base class for audio processing errors."""
    def __init__(self, message: str, status_code: int = 500):
        self.message = message
        self.status_code = status_code
        super().__init__(message)


class UnsupportedFormatError(AudioProcessingError):
    """Raised when the uploaded file has an unsupported format."""
    def __init__(self, extension: str = "", mime_type: str = ""):
        detail = "Unsupported audio format"
        if extension:
            detail += f": '{extension}'"
        if mime_type:
            detail += f" (MIME: {mime_type})"
        super().__init__(detail, status_code=415)


class CorruptedFileError(AudioProcessingError):
    """Raised when the uploaded file is corrupted or unreadable."""
    def __init__(self, detail: str = ""):
        msg = "The uploaded audio file appears to be corrupted or unreadable."
        if detail:
            msg += f" Detail: {detail}"
        super().__init__(msg, status_code=422)


class EmptyAudioError(AudioProcessingError):
    """Raised when the uploaded file contains no audible content."""
    def __init__(self):
        super().__init__(
            "The uploaded audio file contains no audible content or is too short to transcribe.",
            status_code=422,
        )


class FileTooLargeError(AudioProcessingError):
    """Raised when the uploaded file exceeds the size limit."""
    def __init__(self, max_mb: int):
        super().__init__(
            f"File size exceeds the maximum allowed limit of {max_mb} MB.",
            status_code=413,
        )


class TranscriptionError(AudioProcessingError):
    """Raised when Whisper fails to produce a transcript."""
    def __init__(self, detail: str = ""):
        msg = "Transcription failed."
        if detail:
            msg += f" {detail}"
        super().__init__(msg, status_code=500)
