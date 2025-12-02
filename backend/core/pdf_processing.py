"""PDF Validation Utilities for Aithon Core SDK
==============================================

This module provides lightweight PDF validation and metadata extraction utilities.
These are generic utilities used across multiple services for basic PDF operations.

FUNCTIONS PROVIDED:
- PDFValidator.is_valid_pdf()     - Validate if file is a valid PDF
- PDFValidator.get_pdf_info()     - Get PDF metadata (page count, encryption, file size)
- validate_and_get_info()        - Combined validation and info extraction

DEPRECATED CLASSES (with warnings):
- PDFProcessor, SimplePDFProcessor, BasicPDFUtils, PDFProcessorFactory
- quick_extract_text(), quick_get_page_count()

For advanced PDF processing (OCR, layout extraction, batch processing), use:
backend.services.document_processing.utils.pdf_processor.PDFProcessor

USAGE EXAMPLES:
    # Validate PDF
    is_valid = PDFValidator.is_valid_pdf("document.pdf")
    
    # Get PDF info
    info = PDFValidator.get_pdf_info("document.pdf")
    print(f"Pages: {info['page_count']}, Encrypted: {info['is_encrypted']}")
    
    # Combined validation and info
    is_valid, info = validate_and_get_info("document.pdf")
"""

import logging
import warnings
from pathlib import Path
from typing import Dict, Optional, Any

logger = logging.getLogger(__name__)


class PDFValidator:
    """PDF file validation utilities."""

    @staticmethod
    def is_valid_pdf(file_path: str) -> bool:
        """Check if file is a valid PDF."""
        try:
            # Try to import PDF processing library
            try:
                import fitz
            except ImportError:
                logger.warning("PyMuPDF not available for PDF validation")
                return file_path.lower().endswith(".pdf")

            # Try to open the PDF
            doc = fitz.open(file_path)
            page_count = len(doc)
            doc.close()

            return page_count > 0

        except Exception as e:
            logger.error(f"PDF validation failed for {file_path}: {str(e)}")
            return False

    @staticmethod
    def get_pdf_info(file_path: str) -> Optional[Dict[str, Any]]:
        """Get basic information about a PDF file."""
        try:
            import fitz

            doc = fitz.open(file_path)
            info = {
                "page_count": len(doc),
                "metadata": doc.metadata,
                "is_encrypted": doc.needs_pass,
                "file_size": Path(file_path).stat().st_size,
            }
            doc.close()

            return info

        except ImportError:
            logger.warning("PyMuPDF not available for PDF info extraction")
            return None
        except Exception as e:
            logger.error(f"Error getting PDF info for {file_path}: {str(e)}")
            return None


# Deprecated classes - kept for backward compatibility with deprecation warnings

class PDFProcessor:
    """DEPRECATED: Use backend.services.document_processing.utils.pdf_processor.PDFProcessor instead."""
    
    def __init__(self, *args, **kwargs):
        warnings.warn(
            "PDFProcessor from backend.core is deprecated. Use "
            "backend.services.document_processing.utils.pdf_processor.PDFProcessor instead.",
            DeprecationWarning,
            stacklevel=2
        )
        raise NotImplementedError("Use backend.services.document_processing.utils.pdf_processor.PDFProcessor")


class SimplePDFProcessor:
    """DEPRECATED: Use backend.services.document_processing.utils.pdf_processor.PDFProcessor instead."""
    
    def __init__(self, *args, **kwargs):
        warnings.warn(
            "SimplePDFProcessor from backend.core is deprecated. Use "
            "backend.services.document_processing.utils.pdf_processor.PDFProcessor instead.",
            DeprecationWarning,
            stacklevel=2
        )
        raise NotImplementedError("Use backend.services.document_processing.utils.pdf_processor.PDFProcessor")


class BasicPDFUtils:
    """DEPRECATED: Use backend.services.document_processing.utils.pdf_processor.PDFProcessor instead."""
    
    def __init__(self, *args, **kwargs):
        warnings.warn(
            "BasicPDFUtils from backend.core is deprecated. Use "
            "backend.services.document_processing.utils.pdf_processor.PDFProcessor instead.",
            DeprecationWarning,
            stacklevel=2
        )
        raise NotImplementedError("Use backend.services.document_processing.utils.pdf_processor.PDFProcessor")


class PDFProcessorFactory:
    """DEPRECATED: Use backend.services.document_processing.utils.pdf_processor.PDFProcessor instead."""
    
    @staticmethod
    def create_processor(*args, **kwargs):
        warnings.warn(
            "PDFProcessorFactory from backend.core is deprecated. Use "
            "backend.services.document_processing.utils.pdf_processor.PDFProcessor instead.",
            DeprecationWarning,
            stacklevel=2
        )
        raise NotImplementedError("Use backend.services.document_processing.utils.pdf_processor.PDFProcessor")
    
    @staticmethod
    def create_basic_utils(*args, **kwargs):
        warnings.warn(
            "PDFProcessorFactory.create_basic_utils from backend.core is deprecated. Use "
            "backend.services.document_processing.utils.pdf_processor.PDFProcessor instead.",
            DeprecationWarning,
            stacklevel=2
        )
        raise NotImplementedError("Use backend.services.document_processing.utils.pdf_processor.PDFProcessor")


# Deprecated convenience functions
def quick_extract_text(*args, **kwargs):
    """DEPRECATED: Use backend.services.document_processing.utils.pdf_processor.PDFProcessor instead."""
    warnings.warn(
        "quick_extract_text from backend.core is deprecated. Use "
        "backend.services.document_processing.utils.pdf_processor.PDFProcessor instead.",
        DeprecationWarning,
        stacklevel=2
    )
    raise NotImplementedError("Use backend.services.document_processing.utils.pdf_processor.PDFProcessor")


def quick_get_page_count(*args, **kwargs):
    """DEPRECATED: Use backend.services.document_processing.utils.pdf_processor.PDFProcessor instead."""
    warnings.warn(
        "quick_get_page_count from backend.core is deprecated. Use "
        "backend.services.document_processing.utils.pdf_processor.PDFProcessor instead.",
        DeprecationWarning,
        stacklevel=2
    )
    raise NotImplementedError("Use backend.services.document_processing.utils.pdf_processor.PDFProcessor")


def validate_and_get_info(pdf_path: str):
    """Validate PDF and get basic info."""
    is_valid = PDFValidator.is_valid_pdf(pdf_path)
    info = PDFValidator.get_pdf_info(pdf_path) if is_valid else None
    return is_valid, info
