"""
ML Text Extractor - Compatibility Wrapper
========================================

This module provides ML compatibility wrapper for the core PDF processing functionality.
It maintains the same interface as the old ML utilities while leveraging the enhanced
backend PDF processing capabilities.

Features:
- Same interface as old ML utilities for seamless migration
- Enhanced PDF processing through backend PDFProcessor
- OCR fallback and quality assessment
- Batch processing capabilities
"""

import logging
from typing import Dict, List, Tuple

from .core_pdf_processor import PDFProcessor

logger = logging.getLogger(__name__)


class TextExtractor:
    """
    ML compatibility wrapper for PDFProcessor.
    
    This class provides the same interface as the old ML utilities, ensuring backward
    compatibility while leveraging the enhanced backend PDF processing capabilities.
    
    The interface matches the original `extractdata_with_fitz.py` TextExtractor:
    - Simple `extract_text_from_pdf(pdf_path)` → `(text, used_ocr)` interface
    - Batch processing for multiple PDFs
    - Maintains backward compatibility with existing ML code
    
    Features:
    - Same interface as old ML utilities for seamless migration
    - Enhanced PDF processing through backend PDFProcessor
    - OCR fallback and quality assessment
    - Batch processing capabilities
    
    Args:
        max_pages (int): Maximum number of pages to process per document (default: 50)
        min_text_length (int): Minimum text length to consider extraction successful (default: 100)
    
    Example:
        >>> extractor = TextExtractor(max_pages=50)
        >>> text, used_ocr = extractor.extract_text_from_pdf("document.pdf")
        >>> print(f"Extracted {len(text)} characters, OCR used: {used_ocr}")
        
        >>> # Batch processing
        >>> results = extractor.extract_text_batch(["doc1.pdf", "doc2.pdf"])
        >>> for path, result in results.items():
        ...     print(f"{path}: {result['text_length']} chars, success: {result['success']}")
    """
    
    def __init__(self, max_pages: int = 50, min_text_length: int = 100):
        """
        Initialize the text extractor with ML-compatible interface.
        
        Args:
            max_pages: Maximum number of pages to process per document
            min_text_length: Minimum text length to consider extraction successful
        """
        self.pdf_processor = PDFProcessor(
            max_pages=max_pages, 
            min_text_length=min_text_length,
            verbose=False
        )
    
    def extract_text_from_pdf(self, pdf_path: str) -> Tuple[str, bool]:
        """
        Extract text from PDF using the backend PDFProcessor.
        
        Args:
            pdf_path: Path to the PDF file
            
        Returns:
            Tuple of (extracted_text, used_ocr_fallback)
        """
        return self.pdf_processor.extract_text_from_pdf_simple(pdf_path)
    
    def extract_text_batch(self, pdf_paths: list) -> dict:
        """
        Extract text from multiple PDF files using the backend PDFProcessor.
        
        Args:
            pdf_paths: List of PDF file paths
            
        Returns:
            Dictionary mapping file paths to extracted text and metadata
        """
        results = {}
        
        for pdf_path in pdf_paths:
            try:
                text, used_ocr = self.extract_text_from_pdf(pdf_path)
                results[pdf_path] = {
                    "text": text,
                    "used_ocr": used_ocr,
                    "success": len(text.strip()) > 0,
                    "text_length": len(text),
                }
            except Exception as e:
                logger.error(f"Failed to process {pdf_path}: {str(e)}")
                results[pdf_path] = {
                    "text": "",
                    "used_ocr": False,
                    "success": False,
                    "text_length": 0,
                    "error": str(e),
                }
        
        return results
