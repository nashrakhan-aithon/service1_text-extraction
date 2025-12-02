"""
Shared AI utilities for OpenAI API interactions across all applications.
Consolidates common AI operations to reduce code duplication.
"""

import logging
import os
import re
from typing import Dict, Any, List, Optional, Tuple, Union
from enum import Enum
from .config import ConfigManager

# Try to import openai, but make it optional for now
try:
    import openai

    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    print(
        "Warning: OpenAI package not available. AI utilities will have limited functionality."
    )

# Try to import httpx for API mode, but make it optional
try:
    import httpx

    HTTPX_AVAILABLE = True
except ImportError:
    HTTPX_AVAILABLE = False

logger = logging.getLogger(__name__)


class AIMode(str, Enum):
    """AI processing modes."""

    LIBRARY = "library"  # Direct OpenAI API calls
    API = "api"  # Use backend.core_api service
    HYBRID = "hybrid"  # Try API first, fallback to library


class AIUtils:
    """Shared AI utilities for all applications."""

    def __init__(
        self,
        config_manager: Optional[ConfigManager] = None,
        mode: Union[str, AIMode] = None,
        api_base_url: Optional[str] = None,
    ):
        """Initialize with configuration and mode.

        Args:
            config_manager: Configuration manager instance
            mode: AI processing mode (library, api, hybrid)
            api_base_url: Base URL for backend.core_api service
        """
        if config_manager is None:
            # Create default config manager
            config_manager = ConfigManager()

        self.config = config_manager

        # Determine mode from parameter, environment, or default
        if mode is not None:
            self.mode = AIMode(mode)
        else:
            env_mode = os.getenv("AITHON_CORE_AI_MODE", "library")
            self.mode = AIMode(env_mode)

        # Set API base URL
        self.api_base_url = (
            api_base_url or os.getenv("AITHON_CORE_API_URL") or "http://localhost:8000"
        )

        # Initialize OpenAI client for library mode
        if OPENAI_AVAILABLE and self.mode in (AIMode.LIBRARY, AIMode.HYBRID):
            try:
                # Get OpenAI config from config manager
                openai_config = self.config.get_openai_config()
                self.openai_client = openai.OpenAI(api_key=openai_config["api_key"])
                logger.info(f"✅ OpenAI client initialized for {self.mode} mode")
            except Exception as e:
                self.openai_client = None
                logger.warning(f"❌ OpenAI client initialization failed: {str(e)}")
        else:
            self.openai_client = None
            if self.mode in (AIMode.LIBRARY, AIMode.HYBRID):
                logger.warning("OpenAI client not available - package not installed")

        # Initialize HTTP client for API mode
        if HTTPX_AVAILABLE and self.mode in (AIMode.API, AIMode.HYBRID):
            self.http_client = httpx.AsyncClient(timeout=30.0)
            logger.info(
                f"✅ HTTP client initialized for {self.mode} mode (API: {self.api_base_url})"
            )
        else:
            self.http_client = None
            if self.mode in (AIMode.API, AIMode.HYBRID):
                logger.warning(
                    "HTTP client not available - httpx package not installed"
                )

        logger.info(f"🔧 AIUtils initialized in {self.mode} mode")

    async def call_openai_vision(
        self,
        base64_image: str,
        prompt: str,
        model: str = "gpt-4-vision-preview",
        max_tokens: int = 500,
    ) -> str:
        """
        Call OpenAI Vision API with base64 image.

        Args:
            base64_image: Base64 encoded image
            prompt: Text prompt for the vision model
            model: OpenAI model to use
            max_tokens: Maximum tokens in response

        Returns:
            Response text from OpenAI
        """
        if self.mode == AIMode.API:
            return await self._call_vision_api(base64_image, prompt, model, max_tokens)
        elif self.mode == AIMode.HYBRID:
            try:
                return await self._call_vision_api(
                    base64_image, prompt, model, max_tokens
                )
            except Exception as api_error:
                logger.warning(
                    f"API call failed, falling back to library: {str(api_error)}"
                )
                return self._call_vision_library(
                    base64_image, prompt, model, max_tokens
                )
        else:  # AIMode.LIBRARY
            return self._call_vision_library(base64_image, prompt, model, max_tokens)

    async def _call_vision_api(
        self, base64_image: str, prompt: str, model: str, max_tokens: int
    ) -> str:
        """Call vision API via backend.core_api service."""
        if not HTTPX_AVAILABLE or self.http_client is None:
            raise ImportError("httpx package not available for API mode")

        try:
            response = await self.http_client.post(
                f"{self.api_base_url}/ai/vision",
                json={
                    "base64_image": base64_image,
                    "prompt": prompt,
                    "model": model,
                    "max_tokens": max_tokens,
                },
            )
            response.raise_for_status()

            data = response.json()
            if not data.get("success", False):
                raise Exception(
                    f"API call failed: {data.get('error', 'Unknown error')}"
                )

            return data["response_text"]

        except Exception as e:
            logger.error(f"Vision API call error: {str(e)}")
            raise

    def _call_vision_library(
        self, base64_image: str, prompt: str, model: str, max_tokens: int
    ) -> str:
        """Call vision API directly via OpenAI library."""
        if not OPENAI_AVAILABLE or self.openai_client is None:
            raise ImportError(
                "OpenAI package not available. Install openai package to use this functionality."
            )

        try:
            response = self.openai_client.chat.completions.create(
                model=model,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{base64_image}"
                                },
                            },
                        ],
                    }
                ],
                max_tokens=max_tokens,
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"OpenAI Vision library error: {str(e)}")
            raise

    async def call_openai_text(
        self,
        prompt: str,
        system_prompt: str = "",
        model: str = "gpt-4",
        temperature: float = 0,
    ) -> str:
        """
        Call OpenAI text completion API.

        Args:
            prompt: User prompt text
            system_prompt: System prompt (optional)
            model: OpenAI model to use
            temperature: Temperature for response creativity

        Returns:
            Response text from OpenAI
        """
        if self.mode == AIMode.API:
            return await self._call_text_api(prompt, system_prompt, model, temperature)
        elif self.mode == AIMode.HYBRID:
            try:
                return await self._call_text_api(
                    prompt, system_prompt, model, temperature
                )
            except Exception as api_error:
                logger.warning(
                    f"API call failed, falling back to library: {str(api_error)}"
                )
                return self._call_text_library(
                    prompt, system_prompt, model, temperature
                )
        else:  # AIMode.LIBRARY
            return self._call_text_library(prompt, system_prompt, model, temperature)

    async def _call_text_api(
        self, prompt: str, system_prompt: str, model: str, temperature: float
    ) -> str:
        """Call text API via backend.core_api service."""
        if not HTTPX_AVAILABLE or self.http_client is None:
            raise ImportError("httpx package not available for API mode")

        try:
            response = await self.http_client.post(
                f"{self.api_base_url}/ai/text",
                json={
                    "prompt": prompt,
                    "system_prompt": system_prompt,
                    "model": model,
                    "temperature": temperature,
                },
            )
            response.raise_for_status()

            data = response.json()
            if not data.get("success", False):
                raise Exception(
                    f"API call failed: {data.get('error', 'Unknown error')}"
                )

            return data["response_text"]

        except Exception as e:
            logger.error(f"Text API call error: {str(e)}")
            raise

    def _call_text_library(
        self, prompt: str, system_prompt: str, model: str, temperature: float
    ) -> str:
        """Call text API directly via OpenAI library."""
        if not OPENAI_AVAILABLE or self.openai_client is None:
            raise ImportError(
                "OpenAI package not available. Install openai package to use this functionality."
            )

        try:
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})

            response = self.openai_client.chat.completions.create(
                model=model, messages=messages, temperature=temperature
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"OpenAI Text library error: {str(e)}")
            raise

    def parse_json_response(self, response_text: str) -> Tuple[Dict, bool]:
        """
        Parse JSON response from OpenAI with fallback handling.

        Args:
            response_text: Raw response text from OpenAI

        Returns:
            Tuple of (parsed_data, success_flag)
        """
        # Import here to avoid circular imports
        from .json_utils import json_processor

        return json_processor.parse_ai_response(response_text)

    def safe_json_loads(self, text: str) -> Dict:
        """Safely load JSON with error handling."""
        try:
            from .json_utils import json_processor

            return json_processor.safe_json_loads(text)
        except Exception:
            logger.warning(f"Failed to parse JSON: {text[:100]}...")
            return {"error": "JSON parsing failed", "raw_text": text}

    def try_manual_extraction(self, response_content: str) -> List[Dict[str, Any]]:
        """Try to manually extract data when JSON parsing fails."""
        try:
            logger.info("Attempting manual data extraction as fallback...")

            # Extract currency
            currency_match = re.search(
                r"\b(USD|EUR|GBP|€|\$|£)\b", response_content, re.IGNORECASE
            )
            currency = currency_match.group(1) if currency_match else "USD"

            # Extract date patterns
            date_patterns = [
                r"\b(\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{4})\b",
                r"\b(\d{4}-\d{2}-\d{2})\b",
                r"\b(Dec(?:ember)?\s+31,?\s+\d{4})\b",
            ]

            date = None
            for pattern in date_patterns:
                date_match = re.search(pattern, response_content, re.IGNORECASE)
                if date_match:
                    date = date_match.group(1)
                    break

            if not date:
                date = "Unknown"

            # Extract numeric values
            numbers = re.findall(r"\b\d{1,3}(?:,\d{3})*\b", response_content)

            # Create fallback result
            fallback_result = {
                "currency": currency,
                "asofdate": date,
                "lineitems": {
                    "Note": "Manual extraction due to JSON parsing failure",
                    "Numbers_found": len(numbers),
                    "Sample_values": numbers[:5] if numbers else [],
                },
                "extracted_text": response_content,
            }

            logger.warning("Using fallback manual extraction - data may be incomplete")
            return [fallback_result]

        except Exception as e:
            logger.error(f"Manual extraction also failed: {str(e)}")
            return [
                {
                    "currency": None,
                    "asofdate": None,
                    "lineitems": {"error": "All extraction methods failed"},
                    "raw_response": response_content,
                }
            ]

    async def close(self):
        """Close HTTP client connections."""
        if self.http_client is not None:
            await self.http_client.aclose()
            logger.info("🔌 HTTP client connections closed")

    def __del__(self):
        """Cleanup on destruction."""
        # Note: Cannot call async close() from __del__
        # Users should call close() explicitly in async context
        if hasattr(self, "http_client") and self.http_client is not None:
            logger.warning(
                "HTTP client not properly closed. Call await ai_utils.close() in async context."
            )


# Factory functions for easy instantiation
def create_ai_utils(
    app_type: str = "common",
    mode: Union[str, AIMode] = None,
    api_base_url: Optional[str] = None,
) -> AIUtils:
    """Create AIUtils instance with appropriate configuration.

    Args:
        app_type: Application type for configuration
        mode: AI processing mode (library, api, hybrid)
        api_base_url: Base URL for backend.core_api service
    """
    config_manager = ConfigManager(app_type)
    return AIUtils(config_manager, mode, api_base_url)
