"""
Document Text Extraction Service (Service 1)
============================================

Service 1: Extracts text from PDFs and saves .md files to datalake.
This service ONLY handles text extraction - embedding and classification are handled by Service 2.

Service-First Architecture:
- models/: Pydantic models for extraction requests/responses
- routers/: FastAPI routers for extraction endpoints
- services/: Business logic for text extraction operations
"""

from aithon_imports import setup_imports

setup_imports()

from backend.services.document_text_extraction.routers import document_text_extraction_router  # noqa: F401
from backend.services.document_text_extraction.services import (  # noqa: F401
    DocumentTextExtractionService,
    get_progress_tracker,
)

__all__ = ["document_text_extraction_router", "DocumentTextExtractionService", "get_progress_tracker"]

