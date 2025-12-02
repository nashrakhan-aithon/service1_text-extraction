"""
Aithon Core SDK - Shared functionality across all microservices.

This package provides common functionality needed by multiple services:
- File operations (PDF discovery, path resolution)
- PDF processing (loading, text extraction, thumbnails)
- Configuration management
- AI utilities (OpenAI API interactions)
- JSON processing and sanitization
- Text processing utilities
- Status checking and validation
"""

from .file_operations import FileManager, PDFDiscovery
from .pdf_processing import (
    PDFValidator,  # Keep - generic validation only
    # Deprecated: PDFProcessor, PDFProcessorFactory, BasicPDFUtils
)
from .pdf_service import (
    PDFService,
    quick_extract_text,
    quick_extract_full_text,
    quick_convert_to_image,
    quick_get_page_count,
)
from .config import ConfigManager, DatabaseManager
from .types import PDFInfo, ProcessingStatus, ExtractedContent
from .ai_utils import AIUtils, AIMode, create_ai_utils
from .json_utils import JSONProcessor, json_processor
from .text_utils import TextProcessor, text_processor

__version__ = "1.0.0"

__all__ = [
    # Core file operations
    "FileManager",
    "PDFDiscovery",
    # PDF processing (generic validation only)
    "PDFValidator",
    # PDF service
    "PDFService",
    "quick_extract_text",
    "quick_extract_full_text",
    "quick_convert_to_image",
    "quick_get_page_count",
    # Configuration and Database
    "ConfigManager",
    "DatabaseManager",
    # AI utilities
    "AIUtils",
    "AIMode",
    "create_ai_utils",
    # JSON processing
    "JSONProcessor",
    "json_processor",
    # Text processing
    "TextProcessor",
    "text_processor",
    # Types
    "PDFInfo",
    "ProcessingStatus",
    "ExtractedContent",
]
