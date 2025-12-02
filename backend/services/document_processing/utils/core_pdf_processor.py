"""
Core PDF Processing Engine
=========================

This module contains the core PDF processing functionality using PyMuPDF and Tesseract OCR.
It provides the foundational PDF text extraction capabilities used by other modules.

Features:
- Text extraction using PyMuPDF (fitz) with Tesseract OCR fallback
- Password-protected PDF handling with smart retry logic
- Layout preservation and structure analysis
- Batch processing capabilities
- Garbage text detection and quality assessment
- Datalake integration for file management
"""

from aithon_imports import setup_imports

setup_imports()

import logging
import os
import io
import json
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any
import asyncio
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

# Optional imports for ML functionality
try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False
    pd = None

# PDF processing imports
try:
    import fitz  # PyMuPDF
    FITZ_AVAILABLE = True
except ImportError:
    FITZ_AVAILABLE = False
    logging.warning("PyMuPDF (fitz) not available. PDF processing will be limited.")

# OCR imports
try:
    import pytesseract
    from PIL import Image
    PYTESSERACT_AVAILABLE = True
except ImportError:
    PYTESSERACT_AVAILABLE = False
    logging.warning("Tesseract OCR not available. OCR fallback will be disabled.")

from backend.core.config import ConfigManager

logger = logging.getLogger(__name__)


class PDFProcessor:
    """
    Core PDF processing engine with advanced features.
    
    This class provides comprehensive PDF text extraction capabilities using PyMuPDF
    with Tesseract OCR fallback. It handles password-protected PDFs, preserves layout
    information, and includes quality assessment for extracted text.
    
    Features:
    - Text extraction using PyMuPDF (fitz) with Tesseract OCR fallback
    - Password-protected PDF handling with smart retry logic
    - Layout preservation and structure analysis
    - Batch processing capabilities
    - Garbage text detection and quality assessment
    - Datalake integration for file management
    
    Args:
        max_pages (int): Maximum number of pages to process per document (default: 1000)
        min_text_length (int): Minimum text length to consider as meaningful content (default: 50)
        verbose (bool): Enable verbose logging for debugging (default: False)
    
    Example:
        >>> processor = PDFProcessor(max_pages=100, verbose=True)
        >>> result = processor.extract_text_from_pdf("document.pdf")
        >>> if result["success"]:
        ...     print(f"Extracted {result['total_pages']} pages")
        ...     for page_num, page_data in result["pages"].items():
        ...         print(f"Page {page_num}: {len(page_data['text'])} characters")
    """

    def __init__(self, max_pages: int = 1000, min_text_length: int = 50, verbose: bool = False):
        """
        Initialize PDF processor.

        Args:
            max_pages: Maximum number of pages to process per document
            min_text_length: Minimum text length to consider as meaningful content
            verbose: Enable verbose logging for debugging
        """
        self.max_pages = max_pages
        self.min_text_length = min_text_length
        self.verbose = verbose
        self.config = ConfigManager(app_type="common")

        # Get datalake path from configuration
        self.datalake_path = Path(
            self.config.get_var(
                "G_AITHON_DATALAKE",
                section="COMMON",
                fallback="~/projects/aithon/aithon_data/datalake-fcr001",
            )
        )
        self.datalake_path = self.datalake_path.expanduser()

    def extract_text_from_pdf(
        self, pdf_path: str, password: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Extract text from PDF using pymupdf with tesseract fallback.

        This is the core method for PDF text extraction. It attempts to extract text
        using PyMuPDF first, then falls back to Tesseract OCR if the extracted text
        is of poor quality or insufficient length.

        Args:
            pdf_path (str): Path to PDF file
            password (str, optional): Password for encrypted PDFs

        Returns:
            Dict[str, Any]: Dictionary containing extraction results with keys:
                - success (bool): Whether extraction was successful
                - total_pages (int): Number of pages processed
                - pages (dict): Page-by-page extraction results
                - extraction_methods (dict): Method used for each page (fitz/tesseract)
                - layout_info (dict): Layout information for each page
                - error_message (str): Error message if extraction failed
                - password_required (bool): Whether password is required
                - password_used (str): Password that was used successfully

        Example:
            >>> processor = PDFProcessor()
            >>> result = processor.extract_text_from_pdf("document.pdf")
            >>> if result["success"]:
            ...     for page_num, page_data in result["pages"].items():
            ...         print(f"Page {page_num}: {page_data['text'][:100]}...")
        """
        if not FITZ_AVAILABLE:
            raise ImportError("PyMuPDF (fitz) is required for PDF processing")

        result = {
            "success": False,
            "total_pages": 0,
            "pages": {},
            "error_message": None,
            "extraction_methods": {},
            "layout_info": {},
            "password_required": False,
            "password_used": None,
            "attempts_made": 0
        }

        try:
            # Open PDF document
            doc = fitz.open(pdf_path)

            # Handle password-protected PDFs
            if doc.needs_pass:
                if not password:
                    result["error_message"] = (
                        "PDF is password-protected but no password provided"
                    )
                    result["password_required"] = True
                    doc.close()
                    return result

                if not doc.authenticate(password):
                    result["error_message"] = "Incorrect password for PDF"
                    result["password_required"] = True
                    doc.close()
                    return result
                
                result["password_used"] = password

            total_pages = len(doc)
            # Handle max_pages=None (no limit) vs max_pages=int (limit)
            result["total_pages"] = total_pages if self.max_pages is None else min(total_pages, self.max_pages)

            logger.info(f"Processing PDF: {pdf_path} ({result['total_pages']} pages)")

            # Process each page
            for page_num in range(result["total_pages"]):
                try:
                    page_result = self._extract_page_text(doc, page_num, pdf_path)
                    result["pages"][page_num + 1] = page_result
                    result["extraction_methods"][page_num + 1] = page_result["method"]
                    result["layout_info"][page_num + 1] = page_result["layout"]

                    logger.info(
                        f"Page {page_num + 1}: {page_result['method']} - {len(page_result['text'])} chars"
                    )

                except Exception as e:
                    logger.error(f"Error processing page {page_num + 1}: {str(e)}")
                    result["pages"][page_num + 1] = {
                        "text": "",
                        "method": "failed",
                        "layout": {},
                        "error": str(e),
                    }

            doc.close()
            result["success"] = True

        except Exception as e:
            logger.error(f"Error processing PDF {pdf_path}: {str(e)}")
            result["error_message"] = str(e)

        return result

    def extract_text_from_pdf_enhanced(
        self, pdf_path: str, password: Optional[str] = None, 
        file_management_service: Optional[Any] = None
    ) -> Dict[str, Any]:
        """
        Enhanced PDF extraction with smart password handling and 3 attempts.
        
        This method provides advanced password handling for encrypted PDFs. It attempts
        up to 3 different passwords and caches successful passwords for future use.
        
        Args:
            pdf_path (str): Path to PDF file
            password (str, optional): Primary password for encrypted PDFs
            file_management_service (Any, optional): File management service for password caching
            
        Returns:
            Dict[str, Any]: Dictionary containing extraction results with enhanced password handling:
                - success (bool): Whether extraction was successful
                - total_pages (int): Number of pages processed
                - pages (dict): Page-by-page extraction results
                - password_used (str): Password that was used successfully
                - attempts_made (int): Number of password attempts made
                - suggested_passwords (list): List of passwords that were tried
                - error_message (str): Error message if all attempts failed
                
        Example:
            >>> processor = PDFProcessor()
            >>> result = processor.extract_text_from_pdf_enhanced(
            ...     "encrypted.pdf", 
            ...     password="user_password",
            ...     file_management_service=file_service
            ... )
            >>> if result["success"]:
            ...     print(f"Extracted {result['total_pages']} pages using password: {result['password_used']}")
            >>> else:
            ...     print(f"Failed after {result['attempts_made']} attempts")
        """
        if not FITZ_AVAILABLE:
            raise ImportError("PyMuPDF (fitz) is required for PDF processing")

        result = {
            "success": False,
            "total_pages": 0,
            "pages": {},
            "error_message": None,
            "extraction_methods": {},
            "layout_info": {},
            "password_required": False,
            "password_used": None,
            "attempts_made": 0,
            "suggested_passwords": []
        }

        try:
            # Get all possible passwords for 3 attempts
            passwords_to_try = []
            if file_management_service:
                passwords_to_try = file_management_service.get_all_passwords_for_file(pdf_path, password)
            else:
                # Fallback to simple password list
                passwords_to_try = [password, None]
            
            # Limit to 3 attempts
            passwords_to_try = passwords_to_try[:3]
            result["suggested_passwords"] = [pwd for pwd in passwords_to_try if pwd is not None]
            
            # Try each password
            for attempt, pwd in enumerate(passwords_to_try):
                result["attempts_made"] = attempt + 1
                
                try:
                    doc = fitz.open(pdf_path)
                    
                    # Handle password-protected PDFs
                    if doc.needs_pass:
                        if not pwd:
                            doc.close()
                            continue
                        
                        if not doc.authenticate(pwd):
                            doc.close()
                            continue
                    
                    # If we get here, password worked
                    result["password_used"] = pwd
                    
                    # Cache successful password
                    if pwd and file_management_service:
                        file_management_service.save_successful_password(pdf_path, pwd)
                    
                    # Process the document
                    total_pages = len(doc)
                    # Handle max_pages=None (no limit) vs max_pages=int (limit)
                    result["total_pages"] = total_pages if self.max_pages is None else min(total_pages, self.max_pages)
                    
                    logger.info(f"Processing PDF: {pdf_path} ({result['total_pages']} pages) with password attempt {attempt + 1}")
                    
                    # Process each page
                    for page_num in range(result["total_pages"]):
                        try:
                            page_result = self._extract_page_text(doc, page_num, pdf_path)
                            result["pages"][page_num + 1] = page_result
                            result["extraction_methods"][page_num + 1] = page_result["method"]
                            result["layout_info"][page_num + 1] = page_result["layout"]

                            logger.info(
                                f"Page {page_num + 1}: {page_result['method']} - {len(page_result['text'])} chars"
                            )

                        except Exception as e:
                            logger.error(f"Error processing page {page_num + 1}: {str(e)}")
                            result["pages"][page_num + 1] = {
                                "text": "",
                                "method": "failed",
                                "layout": {},
                                "error": str(e),
                            }
                    
                    doc.close()
                    result["success"] = True
                    return result
                    
                except Exception as e:
                    logger.warning(f"Password attempt {attempt + 1} failed for {pdf_path}: {str(e)}")
                    continue
            
            # All attempts failed
            result["error_message"] = f"PDF requires password. Tried {result['attempts_made']} attempts with passwords: {result['suggested_passwords']}"
            result["password_required"] = True

        except Exception as e:
            logger.error(f"Error processing PDF {pdf_path}: {str(e)}")
            result["error_message"] = str(e)

        return result

    def _extract_page_text(
        self, doc: fitz.Document, page_num: int, pdf_path: str
    ) -> Dict[str, Any]:
        """
        Extract text from a single page using fitz, with tesseract fallback.

        Args:
            doc: PyMuPDF document object
            page_num: Page number (0-based)
            pdf_path: Path to PDF file for error reporting

        Returns:
            Dictionary containing page extraction results
        """
        page = doc[page_num]

        # Try fitz extraction first
        try:
            text = page.get_text()
            layout = self._extract_page_layout(page)

            # Check if text is meaningful
            if len(text.strip()) >= self.min_text_length and not self._is_garbage_text(
                text
            ):
                return {
                    "text": text.strip(),
                    "method": "fitz",
                    "layout": layout,
                    "error": None,
                }
        except Exception as e:
            logger.warning(f"Fitz extraction failed for page {page_num + 1}: {str(e)}")

        # Fallback to tesseract OCR
        if PYTESSERACT_AVAILABLE:
            try:
                text, layout = self._extract_with_tesseract(page)
                return {
                    "text": text.strip(),
                    "method": "tesseract",
                    "layout": layout,
                    "error": None,
                }
            except Exception as e:
                logger.warning(
                    f"Tesseract extraction failed for page {page_num + 1}: {str(e)}"
                )
                return {
                    "text": "",
                    "method": "failed",
                    "layout": {},
                    "error": f"Both fitz and tesseract failed: {str(e)}",
                }
        else:
            return {
                "text": "",
                "method": "failed",
                "layout": {},
                "error": "Tesseract not available and fitz extraction failed",
            }

    def _extract_page_layout(self, page: fitz.Page) -> Dict[str, Any]:
        """
        Extract layout information from a page.

        Args:
            page: PyMuPDF page object

        Returns:
            Dictionary containing layout information
        """
        try:
            # Get page dimensions
            rect = page.rect
            layout = {
                "width": rect.width,
                "height": rect.height,
                "rotation": page.rotation,
                "blocks": [],
            }

            # Extract text blocks with positions
            blocks = page.get_text("dict")
            for block in blocks.get("blocks", []):
                if "lines" in block:
                    block_info = {"bbox": block.get("bbox", []), "lines": []}

                    for line in block["lines"]:
                        line_info = {"bbox": line.get("bbox", []), "spans": []}

                        for span in line.get("spans", []):
                            span_info = {
                                "text": span.get("text", ""),
                                "bbox": span.get("bbox", []),
                                "font": span.get("font", ""),
                                "size": span.get("size", 0),
                                "flags": span.get("flags", 0),
                            }
                            line_info["spans"].append(span_info)

                        block_info["lines"].append(line_info)

                    layout["blocks"].append(block_info)

            return layout

        except Exception as e:
            logger.warning(f"Error extracting layout: {str(e)}")
            return {"width": 0, "height": 0, "rotation": 0, "blocks": []}

    def _extract_with_tesseract(self, page: fitz.Page) -> Tuple[str, Dict[str, Any]]:
        """
        Extract text using tesseract OCR.

        Args:
            page: PyMuPDF page object

        Returns:
            Tuple of (extracted_text, layout_info)
        """
        # Convert page to image
        mat = fitz.Matrix(2, 2)  # 2x zoom for better OCR
        pix = page.get_pixmap(matrix=mat)
        img_data = pix.tobytes("png")

        # Load image with PIL
        image = Image.open(io.BytesIO(img_data))

        # Convert to RGB if needed
        if image.mode != "RGB":
            image = image.convert("RGB")

        # Extract text using tesseract
        text = pytesseract.image_to_string(image, lang="eng")

        # Get layout information from tesseract
        layout = self._extract_tesseract_layout(image)

        return text, layout

    def _extract_tesseract_layout(self, image: Image.Image) -> Dict[str, Any]:
        """
        Extract layout information using tesseract.

        Args:
            image: PIL Image object

        Returns:
            Dictionary containing layout information
        """
        try:
            # Get detailed OCR data
            data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)

            layout = {"width": image.width, "height": image.height, "blocks": []}

            # Group words into lines and blocks
            current_block = None
            current_line = None

            for i in range(len(data["text"])):
                text = data["text"][i].strip()
                if not text:
                    continue

                conf = int(data["conf"][i])
                if conf < 30:  # Skip low confidence text
                    continue

                bbox = {
                    "x": data["left"][i],
                    "y": data["top"][i],
                    "width": data["width"][i],
                    "height": data["height"][i],
                }

                # Simple grouping logic (can be improved)
                if current_block is None or abs(bbox["y"] - current_block["y"]) > 20:
                    # New block
                    current_block = {
                        "bbox": [
                            bbox["x"],
                            bbox["y"],
                            bbox["x"] + bbox["width"],
                            bbox["y"] + bbox["height"],
                        ],
                        "lines": [],
                        "y": bbox["y"],
                    }
                    layout["blocks"].append(current_block)
                    current_line = None

                if current_line is None or abs(bbox["y"] - current_line["y"]) > 5:
                    # New line
                    current_line = {
                        "bbox": [
                            bbox["x"],
                            bbox["y"],
                            bbox["x"] + bbox["width"],
                            bbox["y"] + bbox["height"],
                        ],
                        "spans": [],
                        "y": bbox["y"],
                    }
                    current_block["lines"].append(current_line)

                # Add span
                span = {
                    "text": text,
                    "bbox": [
                        bbox["x"],
                        bbox["y"],
                        bbox["x"] + bbox["width"],
                        bbox["y"] + bbox["height"],
                    ],
                    "font": "tesseract",
                    "size": bbox["height"],
                    "flags": 0,
                }
                current_line["spans"].append(span)

            return layout

        except Exception as e:
            logger.warning(f"Error extracting tesseract layout: {str(e)}")
            return {"width": image.width, "height": image.height, "blocks": []}

    def _is_garbage_text(self, text: str) -> bool:
        """
        Check if extracted text appears to be garbage.

        Args:
            text: Extracted text to check

        Returns:
            True if text appears to be garbage
        """
        if not text.strip():
            return True

        # Check for control character patterns (common in Fitz garbage extraction)
        # Look for sequences of control characters like ^@^A^B^C^D^A^E^F^A^G^H
        control_char_count = sum(1 for c in text if ord(c) < 32 and c not in "\t\n\r")
        if control_char_count > len(text) * 0.3:  # More than 30% control characters
            return True

        # Check for specific control character patterns that indicate Fitz garbage
        # Pattern: sequences of control characters (excluding common whitespace)
        import re

        # Exclude common whitespace: \t (9), \n (10), \r (13), space (32)
        control_pattern = r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F-\x9F]+"
        control_sequences = re.findall(control_pattern, text)
        if len(control_sequences) > 3:  # Multiple control character sequences
            return True

        # Check for excessive special characters (excluding common punctuation)
        special_char_ratio = sum(
            1
            for c in text
            if not c.isalnum() and not c.isspace() and c not in ".,!?;:()[]{}\"'"
        ) / len(text)
        if special_char_ratio > 0.5:
            return True

        # Check for repeated characters
        if len(set(text)) < 5:
            return True

        # Check for very short words (likely OCR artifacts)
        words = text.split()
        if len(words) > 0:
            short_word_ratio = sum(1 for w in words if len(w) < 2) / len(words)
            if short_word_ratio > 0.7:
                return True

        # Check for patterns that look like binary data or encoding issues
        # Look for sequences of non-printable characters
        non_printable_count = sum(
            1 for c in text if ord(c) < 32 and c not in "\t\n\r" or ord(c) > 126
        )
        if non_printable_count > len(text) * 0.2:  # More than 20% non-printable
            return True

        # Check for text that's mostly control characters and symbols
        printable_ratio = sum(
            1 for c in text if c.isprintable() and c not in "\t\n\r"
        ) / len(text)
        if printable_ratio < 0.3:  # Less than 30% printable characters
            return True

        return False

    def save_extracted_content(
        self, doc_id: str, extraction_result: Dict[str, Any]
    ) -> Dict[str, str]:
        """
        Save extracted text and layout to datalake folder structure.

        Args:
            doc_id: Document identifier
            extraction_result: Result from extract_text_from_pdf

        Returns:
            Dictionary mapping page numbers to file paths
        """
        doc_folder = self.datalake_path / doc_id
        doc_folder.mkdir(parents=True, exist_ok=True)

        # Create subdirectories
        extracted_text_dir = doc_folder / "extracted_text"
        layout_dir = doc_folder / "layout"
        extracted_text_with_layout_dir = doc_folder / "extracted_text_with_layout"

        extracted_text_dir.mkdir(exist_ok=True)
        layout_dir.mkdir(exist_ok=True)
        extracted_text_with_layout_dir.mkdir(exist_ok=True)

        file_paths = {}

        for page_num, page_data in extraction_result["pages"].items():
            method = page_data["method"]
            text = page_data["text"]
            layout = page_data["layout"]

            # Save extracted text
            text_file = extracted_text_dir / f"page_{page_num:04d}_{method}.md"
            with open(text_file, "w", encoding="utf-8") as f:
                f.write(f"# Page {page_num} - {method.upper()}\n\n")
                f.write(text)

            # Save layout information
            layout_file = layout_dir / f"page_{page_num:04d}_{method}.md"
            with open(layout_file, "w", encoding="utf-8") as f:
                f.write(f"# Page {page_num} Layout - {method.upper()}\n\n")
                f.write(f"```json\n{json.dumps(layout, indent=2)}\n```")

            # Save text with layout recreation
            layout_text_file = (
                extracted_text_with_layout_dir / f"page_{page_num:04d}_{method}.md"
            )
            with open(layout_text_file, "w", encoding="utf-8") as f:
                f.write(self._recreate_text_with_layout(text, layout))

            file_paths[page_num] = {
                "text_file": str(text_file),
                "layout_file": str(layout_file),
                "layout_text_file": str(layout_text_file),
            }

        return file_paths

    def _recreate_text_with_layout(self, text: str, layout: Dict[str, Any]) -> str:
        """
        Recreate text output using layout information to mimic the visual structure.

        Args:
            text: Extracted text
            layout: Layout information

        Returns:
            Formatted text with layout information that mimics the page structure
        """
        result = []

        # Sort blocks by Y position (top to bottom)
        blocks = layout.get("blocks", [])
        sorted_blocks = sorted(blocks, key=lambda b: b.get("bbox", [0, 0, 0, 0])[1])

        current_y = 0

        for block_idx, block in enumerate(sorted_blocks):
            block_bbox = block.get("bbox", [0, 0, 0, 0])
            block_y = block_bbox[1]

            # Calculate spacing from previous block
            if block_idx > 0:
                spacing = block_y - current_y
                if spacing > 20:  # Significant gap - new paragraph
                    result.append("")
                elif spacing > 10:  # Medium gap - line break
                    result.append("")

            # Sort lines within block by Y position
            lines = block.get("lines", [])
            sorted_lines = sorted(lines, key=lambda l: l.get("bbox", [0, 0, 0, 0])[1])

            for line_idx, line in enumerate(sorted_lines):
                line_bbox = line.get("bbox", [0, 0, 0, 0])
                line_x = line_bbox[0]
                line_y = line_bbox[1]

                # Calculate indentation based on X position
                indent_level = max(0, int(line_x / 20))  # 20 units per indent level
                indent = "  " * indent_level

                # Build line text from spans with proper spacing
                line_text = ""
                for span_idx, span in enumerate(line.get("spans", [])):
                    span_text = span.get("text", "").strip()
                    if span_text:
                        # Add space between spans if they're not already separated
                        if (
                            line_text
                            and not line_text.endswith(" ")
                            and not span_text.startswith(" ")
                        ):
                            line_text += " "
                        line_text += span_text

                if line_text.strip():
                    # Add the line with proper indentation
                    result.append(f"{indent}{line_text.strip()}")

                    # Add spacing between lines if there's significant vertical gap
                    if line_idx < len(sorted_lines) - 1:
                        next_line = sorted_lines[line_idx + 1]
                        next_y = next_line.get("bbox", [0, 0, 0, 0])[1]
                        line_spacing = next_y - line_y
                        if line_spacing > 15:  # Significant line spacing
                            result.append("")  # Add blank line

            current_y = block_bbox[3]  # Bottom of current block

        return "\n".join(result)

    def extract_text_batch(self, pdf_paths: List[str]) -> Dict[str, Any]:
        """
        Extract text from multiple PDF files (enhanced from ML utils).
        
        Args:
            pdf_paths: List of PDF file paths
            
        Returns:
            Dictionary mapping file paths to extracted text and metadata
        """
        results = {}
        
        if self.verbose:
            logger.info(f"Starting batch processing of {len(pdf_paths)} PDF files")
        
        for i, pdf_path in enumerate(pdf_paths):
            try:
                if self.verbose:
                    logger.info(f"Processing file {i+1}/{len(pdf_paths)}: {pdf_path}")
                
                # Use existing extract_text_from_pdf method
                extraction_result = self.extract_text_from_pdf(pdf_path)
                
                if extraction_result["success"]:
                    # Combine all page text
                    combined_text = ""
                    for page_num, page_data in extraction_result["pages"].items():
                        if page_data.get("text", "").strip():
                            combined_text += f"\n--- PAGE {page_num} ---\n{page_data['text']}\n"
                    
                    # Count pages that used OCR
                    ocr_pages = sum(1 for method in extraction_result["extraction_methods"].values() 
                                  if method == "tesseract")
                    
                    results[pdf_path] = {
                        "text": combined_text.strip(),
                        "used_ocr": ocr_pages > 0,
                        "success": True,
                        "text_length": len(combined_text.strip()),
                        "total_pages": extraction_result["total_pages"],
                        "ocr_pages": ocr_pages,
                        "extraction_methods": extraction_result["extraction_methods"],
                        "password_used": extraction_result.get("password_used"),
                        "password_required": extraction_result.get("password_required", False)
                    }
                else:
                    results[pdf_path] = {
                        "text": "",
                        "used_ocr": False,
                        "success": False,
                        "text_length": 0,
                        "error": extraction_result.get("error_message", "Unknown error"),
                        "password_required": extraction_result.get("password_required", False)
                    }
                    
            except Exception as e:
                logger.error(f"Failed to process {pdf_path}: {str(e)}")
                results[pdf_path] = {
                    "text": "",
                    "used_ocr": False,
                    "success": False,
                    "text_length": 0,
                    "error": str(e),
                    "password_required": False
                }
        
        if self.verbose:
            successful = sum(1 for r in results.values() if r.get("success", False))
            logger.info(f"Batch processing completed: {successful}/{len(pdf_paths)} successful")
        
        return results

    def extract_text_batch_enhanced(self, pdf_paths: List[str], passwords: Optional[List[str]] = None, 
                                   file_management_service: Optional[Any] = None) -> Dict[str, Any]:
        """
        Enhanced batch extraction with smart password handling and 3 attempts.
        
        Args:
            pdf_paths: List of PDF file paths
            passwords: Optional list of passwords for encrypted PDFs
            file_management_service: Optional file management service for password caching
            
        Returns:
            Dictionary mapping file paths to extracted text and metadata
        """
        results = {}
        
        if self.verbose:
            logger.info(f"Starting enhanced batch processing of {len(pdf_paths)} PDF files")
        
        for i, pdf_path in enumerate(pdf_paths):
            try:
                if self.verbose:
                    logger.info(f"Processing file {i+1}/{len(pdf_paths)}: {pdf_path}")
                
                # Get password for this file
                password = None
                if passwords and i < len(passwords):
                    password = passwords[i]
                
                # Use enhanced extraction
                extraction_result = self.extract_text_from_pdf_enhanced(
                    pdf_path, password, file_management_service
                )
                
                if extraction_result["success"]:
                    # Combine all page text
                    combined_text = ""
                    for page_num, page_data in extraction_result["pages"].items():
                        if page_data.get("text", "").strip():
                            combined_text += f"\n--- PAGE {page_num} ---\n{page_data['text']}\n"
                    
                    # Count pages that used OCR
                    ocr_pages = sum(1 for method in extraction_result["extraction_methods"].values() 
                                  if method == "tesseract")
                    
                    results[pdf_path] = {
                        "text": combined_text.strip(),
                        "used_ocr": ocr_pages > 0,
                        "success": True,
                        "text_length": len(combined_text.strip()),
                        "total_pages": extraction_result["total_pages"],
                        "ocr_pages": ocr_pages,
                        "extraction_methods": extraction_result["extraction_methods"],
                        "password_used": extraction_result.get("password_used"),
                        "password_required": extraction_result.get("password_required", False),
                        "attempts_made": extraction_result.get("attempts_made", 0),
                        "suggested_passwords": extraction_result.get("suggested_passwords", [])
                    }
                else:
                    results[pdf_path] = {
                        "text": "",
                        "used_ocr": False,
                        "success": False,
                        "text_length": 0,
                        "error": extraction_result.get("error_message", "Unknown error"),
                        "password_required": extraction_result.get("password_required", False),
                        "attempts_made": extraction_result.get("attempts_made", 0),
                        "suggested_passwords": extraction_result.get("suggested_passwords", [])
                    }
                    
            except Exception as e:
                logger.error(f"Failed to process {pdf_path}: {str(e)}")
                results[pdf_path] = {
                    "text": "",
                    "used_ocr": False,
                    "success": False,
                    "text_length": 0,
                    "error": str(e),
                    "password_required": False,
                    "attempts_made": 0,
                    "suggested_passwords": []
                }
        
        if self.verbose:
            successful = sum(1 for r in results.values() if r.get("success", False))
            password_required = sum(1 for r in results.values() if r.get("password_required", False))
            logger.info(f"Enhanced batch processing completed: {successful}/{len(pdf_paths)} successful, {password_required} require passwords")
        
        return results

    def _extract_page_with_tesseract_enhanced(self, page: fitz.Page) -> str:
        """
        Enhanced OCR extraction with better configuration (from ML utils).
        
        Args:
            page: PyMuPDF page object
            
        Returns:
            Extracted text string
        """
        if not PYTESSERACT_AVAILABLE:
            return ""
            
        try:
            # Validate that page is a fitz page object
            if not hasattr(page, 'get_pixmap'):
                raise ValueError(f"Invalid page object: expected fitz.Page, got {type(page)}")
            
            # Convert page to image with higher resolution for better OCR
            mat = fitz.Matrix(2, 2)  # 2x zoom for better OCR
            pix = page.get_pixmap(matrix=mat)
            img_data = pix.tobytes("png")

            # Load image with PIL
            image = Image.open(io.BytesIO(img_data))

            # Convert to RGB if needed
            if image.mode != "RGB":
                image = image.convert("RGB")

            # Extract text using tesseract with better configuration
            # Use PSM 6 (uniform block of text) for better results
            text = pytesseract.image_to_string(
                image, 
                lang="eng",
                config="--psm 6 --oem 3"  # PSM 6: uniform block, OEM 3: default engine
            )
            
            # Clean up the text
            text = text.strip()
            
            # Check if OCR produced meaningful text
            if len(text) < 10 or self._is_garbage_text(text):
                if self.verbose:
                    logger.warning("OCR produced poor quality text, trying alternative configuration")
                # Try with different PSM mode
                text = pytesseract.image_to_string(
                    image, 
                    lang="eng",
                    config="--psm 3 --oem 3"  # PSM 3: fully automatic page segmentation
                ).strip()
            
            return text

        except Exception as e:
            logger.error(f"Enhanced Tesseract OCR failed: {str(e)}")
            return ""

    def set_verbose_mode(self, verbose: bool) -> None:
        """
        Enable or disable verbose logging.
        
        Args:
            verbose: True to enable verbose logging, False to disable
        """
        self.verbose = verbose
        if verbose:
            logger.info("Verbose mode enabled for PDF processing")
        else:
            logger.info("Verbose mode disabled for PDF processing")

    def get_processing_stats(self) -> Dict[str, Any]:
        """
        Get processing statistics (placeholder for future enhancement).
        
        Returns:
            Dictionary containing processing statistics
        """
        return {
            "max_pages": self.max_pages,
            "min_text_length": self.min_text_length,
            "verbose": self.verbose,
            "fitz_available": FITZ_AVAILABLE,
            "tesseract_available": PYTESSERACT_AVAILABLE
        }

    def extract_text_from_pdf_simple(self, pdf_path: str) -> Tuple[str, bool]:
        """
        Simple interface for ML compatibility - returns (text, used_ocr) tuple.
        
        Args:
            pdf_path: Path to PDF file
            
        Returns:
            Tuple of (extracted_text, used_ocr_fallback)
        """
        result = self.extract_text_from_pdf(pdf_path)
        
        if not result["success"]:
            return "", False
        
        # Combine all page text
        combined_text = ""
        used_ocr = False
        
        for page_num, page_data in result["pages"].items():
            if page_data.get("text", "").strip():
                combined_text += f"\n--- PAGE {page_num} ---\n{page_data['text']}\n"
                if page_data.get("method") == "tesseract":
                    used_ocr = True
        
        return combined_text.strip(), used_ocr
