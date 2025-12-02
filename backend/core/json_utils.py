"""
Shared JSON processing utilities for robust parsing and sanitization.
Consolidates JSON handling from all applications to reduce code duplication.
"""

import json
import re
import logging
from typing import Dict, Any, List, Optional, Union, Tuple

logger = logging.getLogger(__name__)


class JSONProcessor:
    """Comprehensive JSON processing utilities for AI responses and file handling."""

    def __init__(self):
        """Initialize JSON processor with default settings."""
        self.company_name_fixes = [
            (r"Domino's", "Dominos"),
            (r"McDonald's", "McDonalds"),
            (r"Wendy's", "Wendys"),
            (r"Papa John's", "Papa Johns"),
            (r"Denny's", "Dennys"),
            (r"'s\s+(Inc|Corp|LLC|Ltd)", r"s \1"),  # Generic 's Company patterns
        ]

    def sanitize_json_string(self, json_str: str) -> str:
        """
        Sanitize a JSON string to handle common parsing issues from AI-generated content.

        This function fixes:
        1. Unescaped quotes and apostrophes in string values
        2. Unescaped newlines and control characters
        3. Trailing commas
        4. Invalid escape sequences
        5. Common company name issues

        Args:
            json_str: Raw JSON string that may have parsing issues

        Returns:
            Sanitized JSON string that should parse correctly
        """
        try:
            # First, try to parse as-is
            json.loads(json_str)
            return json_str
        except json.JSONDecodeError:
            pass

        # Apply sanitization fixes
        sanitized = json_str

        # Fix 1: Handle unescaped quotes in string values
        def fix_inner_quotes(match):
            full_match = match.group(0)
            key_part = match.group(1)  # The key part: "key":
            value_content = match.group(2)  # Content between outer quotes

            # Escape any unescaped quotes within the value
            escaped_content = value_content.replace('"', '\\"').replace("'", "\\'")
            return f'{key_part}"{escaped_content}"'

        # Pattern to match "key": "value with 'quotes' inside"
        quote_pattern = r'("[^"]*":\s*")(.*?)("(?:\s*[,}\]]|$))'
        sanitized = re.sub(quote_pattern, fix_inner_quotes, sanitized, flags=re.DOTALL)

        # Fix 2: Handle unescaped newlines and control characters in string values
        def fix_control_chars(match):
            full_match = match.group(0)
            key_part = match.group(1)
            value_content = match.group(2)
            end_part = match.group(3)

            # Escape control characters
            escaped_content = (
                value_content.replace("\n", "\\n")
                .replace("\r", "\\r")
                .replace("\t", "\\t")
                .replace("\b", "\\b")
                .replace("\f", "\\f")
            )
            return f'{key_part}"{escaped_content}"{end_part}'

        # Apply control character fixes
        control_pattern = r'("[^"]*":\s*")(.*?)("(?:\s*[,}\]]|$))'
        sanitized = re.sub(
            control_pattern, fix_control_chars, sanitized, flags=re.DOTALL
        )

        # Fix 3: Remove trailing commas before } or ]
        sanitized = re.sub(r",(\s*[}\]])", r"\1", sanitized)

        # Fix 4: Handle common company name issues (like "Domino's Pizza")
        for pattern, replacement in self.company_name_fixes:
            sanitized = re.sub(pattern, replacement, sanitized)

        return sanitized

    def safe_json_loads(
        self, json_str: str, use_sanitization: bool = True
    ) -> Dict[str, Any]:
        """
        Safely load JSON with automatic sanitization for common AI-generated JSON issues.

        Args:
            json_str: JSON string to parse
            use_sanitization: Whether to attempt sanitization on parse failure

        Returns:
            Parsed JSON data as dictionary

        Raises:
            json.JSONDecodeError: If all parsing attempts fail
        """
        try:
            # Try original first
            return json.loads(json_str)
        except json.JSONDecodeError as e:
            logger.warning(f"JSON parsing error: {str(e)}")

            if use_sanitization:
                logger.info("Attempting to sanitize JSON...")
                try:
                    # Apply sanitization
                    sanitized = self.sanitize_json_string(json_str)
                    result = json.loads(sanitized)
                    logger.info("JSON sanitization successful!")
                    return result
                except json.JSONDecodeError as e2:
                    logger.error(f"JSON sanitization failed: {str(e2)}")
                    logger.error(
                        f"Problematic JSON snippet: {json_str[max(0, e2.pos-50):e2.pos+50]}"
                    )
                    raise e2
            else:
                raise e

    def parse_ai_response(self, response_text: str) -> Tuple[Dict[str, Any], bool]:
        """
        Parse JSON response from AI with multiple fallback strategies.

        Args:
            response_text: Raw response text from AI model

        Returns:
            Tuple of (parsed_data, success_flag)
        """
        if not response_text or not response_text.strip():
            logger.warning("Empty or whitespace-only AI response")
            return {}, False

        try:
            # Strategy 1: Direct JSON parsing
            if response_text.strip().startswith(
                "{"
            ) or response_text.strip().startswith("["):
                return self.safe_json_loads(response_text), True

            # Strategy 2: Extract JSON from markdown code blocks
            json_match = re.search(
                r"```(?:json)?\s*(\{.*?\}|\[.*?\])\s*```", response_text, re.DOTALL
            )
            if json_match:
                return self.safe_json_loads(json_match.group(1)), True

            # Strategy 3: Extract JSON that might not be in code blocks
            json_match = re.search(r"(\{.*?\}|\[.*?\])", response_text, re.DOTALL)
            if json_match:
                return self.safe_json_loads(json_match.group(1)), True

            # Strategy 4: Look for JSON in different formats
            # Try to find JSON block in markdown format (alternative pattern)
            json_match = re.search(r"```json\n(.*?)\n```", response_text, re.DOTALL)
            if json_match:
                return self.safe_json_loads(json_match.group(1)), True

            logger.warning("Could not find valid JSON in AI response")
            return {}, False

        except json.JSONDecodeError as e:
            logger.error(f"All JSON parsing strategies failed: {str(e)}")
            return {}, False

    def load_json_from_file(
        self, file_path: str, remove_markdown: bool = True
    ) -> Optional[Dict[str, Any]]:
        """
        Load JSON data from a file with optional markdown removal.

        Args:
            file_path: Path to the JSON file
            remove_markdown: Whether to remove markdown code block markers

        Returns:
            Loaded JSON data or None if loading fails
        """
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read().strip()

            if remove_markdown:
                # Remove markdown code block markers if present
                if content.startswith("```json"):
                    content = content[7:]
                if content.endswith("```"):
                    content = content[:-3]
                content = content.strip()

            return self.safe_json_loads(content)

        except FileNotFoundError:
            logger.error(f"JSON file not found: {file_path}")
            return None
        except Exception as e:
            logger.error(f"Error loading JSON from {file_path}: {str(e)}")
            return None

    def save_json_to_file(
        self,
        data: Dict[str, Any],
        file_path: str,
        indent: int = 2,
        ensure_ascii: bool = False,
    ) -> bool:
        """
        Save JSON data to a file with proper formatting.

        Args:
            data: Data to save as JSON
            file_path: Path where to save the file
            indent: Indentation for pretty printing
            ensure_ascii: Whether to escape non-ASCII characters

        Returns:
            True if successful, False otherwise
        """
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=indent, ensure_ascii=ensure_ascii)
            return True
        except Exception as e:
            logger.error(f"Error saving JSON to {file_path}: {str(e)}")
            return False

    def validate_json_structure(
        self, data: Dict[str, Any], required_keys: List[str]
    ) -> Tuple[bool, List[str]]:
        """
        Validate that JSON data contains required keys.

        Args:
            data: JSON data to validate
            required_keys: List of required key names

        Returns:
            Tuple of (is_valid, missing_keys)
        """
        if not isinstance(data, dict):
            return False, ["Data is not a dictionary"]

        missing_keys = [key for key in required_keys if key not in data]
        return len(missing_keys) == 0, missing_keys

    def merge_json_objects(self, *objects: Dict[str, Any]) -> Dict[str, Any]:
        """
        Merge multiple JSON objects into one, with later objects overriding earlier ones.

        Args:
            *objects: Variable number of dictionaries to merge

        Returns:
            Merged dictionary
        """
        result = {}
        for obj in objects:
            if isinstance(obj, dict):
                result.update(obj)
        return result


# Create a global instance for easy access
json_processor = JSONProcessor()


# Convenience functions for backward compatibility
def sanitize_json_string(json_str: str) -> str:
    """Backward compatibility wrapper for sanitize_json_string."""
    return json_processor.sanitize_json_string(json_str)


def safe_json_loads(json_str: str) -> Dict[str, Any]:
    """Backward compatibility wrapper for safe_json_loads."""
    return json_processor.safe_json_loads(json_str)
