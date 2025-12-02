"""PDF Operations Service for Aithon Core SDK
============================================

This module provides simple PDF operations with context management and convenience functions.
Designed for basic PDF operations across multiple services.

FUNCTIONS PROVIDED:
- PDFService.open_pdf()           - Open PDF and get page count
- PDFService.extract_text()       - Extract text from single page
- PDFService.extract_full_text()  - Extract text from all pages with page markers
- PDFService.convert_to_image()   - Convert page to base64 image
- PDFService.get_pdf_info()       - Get detailed PDF metadata with page dimensions
- Context manager support         - Use with 'with' statements for automatic cleanup

CONVENIENCE FUNCTIONS:
- quick_extract_text()            - One-liner text extraction from single page
- quick_extract_full_text()       - One-liner text extraction from entire PDF
- quick_convert_to_image()        - One-liner page to image conversion
- quick_get_page_count()          - One-liner page count retrieval

USAGE EXAMPLES:
    # Context manager (recommended)
    with PDFService() as pdf:
        pdf.open_pdf("document.pdf")
        text = pdf.extract_text(0)  # First page
        image = pdf.convert_to_image(0, zoom=2.0)
    
    # Convenience functions
    text = quick_extract_text("document.pdf", 0)
    full_text = quick_extract_full_text("document.pdf")
    image = quick_convert_to_image("document.pdf", 0)
    page_count = quick_get_page_count("document.pdf")
    
    # Manual usage
    pdf = PDFService()
    pdf.open_pdf("document.pdf")
    info = pdf.get_pdf_info()
    pdf.close()
"""

import base64
import io
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from abc import ABC, abstractmethod

from .types import ExtractedContent, ProcessingStatus, PDFInfo

# Try to import optional dependencies
try:
    import fitz  # PyMuPDF

    FITZ_AVAILABLE = True
except ImportError:
    FITZ_AVAILABLE = False
    print("Warning: PyMuPDF (fitz) not available. PDF processing will be limited.")

try:
    import pytesseract

    PYTESSERACT_AVAILABLE = True
except ImportError:
    PYTESSERACT_AVAILABLE = False
    print("Warning: pytesseract not available. OCR functionality will be limited.")

try:
    from PIL import Image

    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    print("Warning: PIL not available. Image processing will be limited.")

logger = logging.getLogger(__name__)


class PDFService:
    """Unified PDF service for all backend services."""

    def __init__(self):
        self.doc = None
        self.pdf_path = None

    def open_pdf(self, pdf_path: str) -> int:
        """Open PDF file and return number of pages."""
        if not FITZ_AVAILABLE:
            raise ImportError("PyMuPDF (fitz) is required for PDF processing")

        try:
            self.doc = fitz.open(pdf_path)
            self.pdf_path = pdf_path
            return len(self.doc)
        except Exception as e:
            logger.error(f"Error opening PDF {pdf_path}: {str(e)}")
            raise Exception(f"Error opening PDF: {str(e)}")

    def extract_text(self, page_num: int) -> str:
        """Extract text from specific page."""
        if not self.doc:
            raise Exception("PDF not opened. Call open_pdf() first.")

        try:
            page = self.doc[page_num]
            text = page.get_text()
            return text.strip()
        except Exception as e:
            logger.error(f"Error extracting text from page {page_num}: {str(e)}")
            raise Exception(f"Error extracting text from page {page_num}: {str(e)}")

    def extract_full_text(self) -> str:
        """Extract text from all pages."""
        if not self.doc:
            raise Exception("PDF not opened. Call open_pdf() first.")

        try:
            full_text = ""
            for page_num in range(len(self.doc)):
                page_text = self.extract_text(page_num)
                full_text += f"\n--- Page {page_num + 1} ---\n{page_text}\n"
            return full_text.strip()
        except Exception as e:
            logger.error(f"Error extracting full text: {str(e)}")
            raise Exception(f"Error extracting full text: {str(e)}")

    def convert_to_image(self, page_num: int, zoom: float = 2.0) -> str:
        """Convert PDF page to base64 image."""
        if not self.doc:
            raise Exception("PDF not opened. Call open_pdf() first.")

        try:
            page = self.doc[page_num]
            mat = fitz.Matrix(zoom, zoom)
            pix = page.get_pixmap(matrix=mat)
            img_data = pix.tobytes("png")

            # Convert to base64
            img_base64 = base64.b64encode(img_data).decode("utf-8")
            return img_base64
        except Exception as e:
            logger.error(f"Error converting page {page_num} to image: {str(e)}")
            raise Exception(f"Error converting page {page_num} to image: {str(e)}")

    def get_pdf_info(self) -> Dict[str, Any]:
        """Get PDF metadata and information."""
        if not self.doc:
            raise Exception("PDF not opened. Call open_pdf() first.")

        try:
            metadata = self.doc.metadata
            page_count = len(self.doc)

            # Get page dimensions
            pages_info = []
            for page_num in range(page_count):
                page = self.doc[page_num]
                pages_info.append(
                    {
                        "page_num": page_num,
                        "width": page.rect.width,
                        "height": page.rect.height,
                    }
                )

            return {
                "page_count": page_count,
                "metadata": metadata,
                "pages": pages_info,
                "file_path": self.pdf_path,
            }
        except Exception as e:
            logger.error(f"Error getting PDF info: {str(e)}")
            raise Exception(f"Error getting PDF info: {str(e)}")

    def close(self):
        """Close PDF document."""
        if self.doc:
            self.doc.close()
            self.doc = None
            self.pdf_path = None

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()


# Convenience functions for quick operations
def quick_extract_text(pdf_path: str, page_num: int) -> str:
    """Quick text extraction from PDF page."""
    with PDFService() as pdf_service:
        pdf_service.open_pdf(pdf_path)
        return pdf_service.extract_text(page_num)


def quick_extract_full_text(pdf_path: str) -> str:
    """Quick text extraction from entire PDF."""
    with PDFService() as pdf_service:
        pdf_service.open_pdf(pdf_path)
        return pdf_service.extract_full_text()


def quick_convert_to_image(pdf_path: str, page_num: int, zoom: float = 2.0) -> str:
    """Quick PDF page to image conversion."""
    with PDFService() as pdf_service:
        pdf_service.open_pdf(pdf_path)
        return pdf_service.convert_to_image(page_num, zoom)


def quick_get_page_count(pdf_path: str) -> int:
    """Quick page count retrieval."""
    with PDFService() as pdf_service:
        return pdf_service.open_pdf(pdf_path)
