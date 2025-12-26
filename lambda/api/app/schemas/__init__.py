"""
Pydantic schemas for API request/response validation
"""
from .ocr import OcrWord, OcrResult, OcrResultResponse, OcrStartRequest
from .upload import PresignedUrlRequest, PresignedUrlResponse, UploadCompleteRequest
from .extraction import ExtractionRequest, ExtractionResult
from .schema import SchemaField, SchemaGenerateRequest, SchemaSaveRequest
from .job import JobStatus, JobStartResponse
from .image import ImageInfo, ImageListResponse
from .app import AppCreateRequest, AppUpdateRequest, CustomPromptRequest
from .common import ErrorResponse, SuccessResponse

__all__ = [
    # OCR
    "OcrWord",
    "OcrResult",
    "OcrResultResponse",
    "OcrStartRequest",
    # Upload
    "PresignedUrlRequest",
    "PresignedUrlResponse",
    "UploadCompleteRequest",
    # Extraction
    "ExtractionRequest",
    "ExtractionResult",
    # Schema
    "SchemaField",
    "SchemaGenerateRequest",
    "SchemaSaveRequest",
    # Job
    "JobStatus",
    "JobStartResponse",
    # Image
    "ImageInfo",
    "ImageListResponse",
    # App
    "AppCreateRequest",
    "AppUpdateRequest",
    "CustomPromptRequest",
    # Common
    "ErrorResponse",
    "SuccessResponse",
]
