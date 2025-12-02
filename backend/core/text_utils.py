"""
Shared text processing utilities for all applications.
Provides common text operations like cleaning, formatting, etc.
"""

import re
import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)


class TextProcessor:
    """Shared text processing utilities."""

    def clean_unicode(self, text: str) -> str:
        """Clean up Unicode and special character issues in extracted text."""
        # Common currency symbol mappings
        currency_replacements = {
            "���": "€",  # Common Euro symbol corruption
            "â‚¬": "€",  # Another Euro corruption
            "\u20ac": "€",  # Euro symbol
            "\u00a3": "£",  # Pound symbol
            "\u00a5": "¥",  # Yen symbol
            "\u0024": "$",  # Dollar symbol
        }

        # Common unicode replacements
        unicode_replacements = {
            "\u00a0": " ",  # Non-breaking space
            "\u2010": "-",  # Hyphen
            "\u2011": "-",  # Non-breaking hyphen
            "\u2012": "-",  # Figure dash
            "\u2013": "-",  # En dash
            "\u2014": "-",  # Em dash
            "\u2015": "-",  # Horizontal bar
            "\u2018": "'",  # Left single quote
            "\u2019": "'",  # Right single quote
            "\u201a": "'",  # Single low quote
            "\u201c": '"',  # Left double quote
            "\u201d": '"',  # Right double quote
            "\u201e": '"',  # Double low quote
            "\u2026": "...",  # Ellipsis
            "\ufeff": "",  # Remove BOM
        }

        # Apply currency replacements
        for corrupted, correct in currency_replacements.items():
            text = text.replace(corrupted, correct)

        # Apply unicode replacements
        for old, new in unicode_replacements.items():
            text = text.replace(old, new)

        # Clean up any remaining problematic characters
        cleaned_text = ""
        for char in text:
            if ord(char) < 32:  # Control characters
                if char in ["\n", "\r", "\t"]:  # Keep important whitespace
                    cleaned_text += char
                else:
                    cleaned_text += " "  # Replace other control chars with space
            elif ord(char) > 127:  # Non-ASCII characters
                # Keep common financial/currency Unicode characters
                if char in ["€", "£", "¥", "¢", "₹", "₽", "₩", "₪", "₫"]:
                    cleaned_text += char
                elif ord(char) < 256:  # Extended ASCII
                    cleaned_text += char
                else:
                    # Replace unknown Unicode with space
                    cleaned_text += " "
            else:
                cleaned_text += char

        return cleaned_text

    def chunk_text(
        self, text: str, max_chars: int = 8000, overlap: int = 200
    ) -> List[str]:
        """
        Split text into chunks for processing.

        Args:
            text: Text to chunk
            max_chars: Maximum characters per chunk
            overlap: Character overlap between chunks

        Returns:
            List of text chunks
        """
        if len(text) <= max_chars:
            return [text]

        chunks = []
        start = 0

        while start < len(text):
            # Find end position
            end = start + max_chars

            if end >= len(text):
                # Last chunk
                chunks.append(text[start:])
                break

            # Try to break at sentence or paragraph
            break_pos = end
            for break_char in ["\n\n", "\n", ". ", "! ", "? "]:
                pos = text.rfind(break_char, start, end)
                if pos > start:
                    break_pos = pos + len(break_char)
                    break

            chunks.append(text[start:break_pos])
            start = break_pos - overlap if overlap > 0 else break_pos

        return chunks

    def extract_numbers(self, text: str) -> List[str]:
        """Extract numeric values from text."""
        # Pattern for numbers with commas and decimals
        number_pattern = r"\b\d{1,3}(?:,\d{3})*(?:\.\d{1,2})?\b"
        return re.findall(number_pattern, text)

    def extract_dates(self, text: str) -> List[str]:
        """Extract date patterns from text."""
        date_patterns = [
            r"\b\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\w*\s+\d{4}\b",
            r"\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\w*\s+\d{1,2},?\s+\d{4}\b",
            r"\b\d{4}-\d{2}-\d{2}\b",
            r"\b\d{1,2}/\d{1,2}/\d{4}\b",
            r"\b\d{1,2}\.\d{1,2}\.\d{4}\b",
        ]

        dates = []
        for pattern in date_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            dates.extend(matches)

        return dates

    def normalize_whitespace(self, text: str) -> str:
        """Normalize whitespace in text."""
        # Replace multiple spaces/tabs/newlines with single space
        text = re.sub(r"\s+", " ", text)
        # Remove leading/trailing whitespace
        return text.strip()

    def remove_page_headers_footers(self, text: str) -> str:
        """Remove common page headers and footers."""
        lines = text.split("\n")
        cleaned_lines = []

        for line in lines:
            line = line.strip()
            # Skip common header/footer patterns
            if (
                re.match(r"^Page \d+$", line, re.IGNORECASE)
                or re.match(r"^\d+$", line)
                or len(line) < 3
                or re.match(r"^-+$", line)
            ):
                continue
            cleaned_lines.append(line)

        return "\n".join(cleaned_lines)


# Create a global instance for easy access
text_processor = TextProcessor()


# Convenience functions for backward compatibility
def clean_unicode(text: str) -> str:
    """Backward compatibility wrapper for clean_unicode."""
    return text_processor.clean_unicode(text)


def chunk_text(text: str, max_chars: int = 8000, overlap: int = 200) -> List[str]:
    """Backward compatibility wrapper for chunk_text."""
    return text_processor.chunk_text(text, max_chars, overlap)
