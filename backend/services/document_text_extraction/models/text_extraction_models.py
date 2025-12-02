from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class TextExtractionProgress(BaseModel):
    """Progress payload for text extraction batches."""

    batch_id: str
    status: str
    total_documents: int = 0
    processed_documents: int = 0
    total_pages: int = 0
    processed_pages: int = 0
    progress_percentage: int = 0
    current_document: Optional[str] = None
    current_stage: Optional[str] = None
    current_operation: Optional[str] = None
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    results: List[Dict[str, Any]] = Field(default_factory=list)
    errors: List[Any] = Field(default_factory=list)


class TextExtractionServiceInfo(BaseModel):
    """Metadata for service root endpoint."""

    service: str
    version: str
    status: str
    description: str
    service_first_architecture: bool
    available_endpoints: Dict[str, str]


class TextExtractionHealth(BaseModel):
    """Health response for text extraction service."""

    service: str
    status: str
    capabilities: List[str]


class TextExtractionRequest(BaseModel):
    """Request model for text extraction endpoint."""

    queue_ids: List[int] = Field(..., description="List of queue item IDs to process")
    batch_id: Optional[str] = Field(None, description="Optional batch ID for progress tracking")


class TextExtractionResponse(BaseModel):
    """Response model for text extraction endpoint."""

    success: bool
    message: str
    processed_count: int
    failed_count: int
    batch_id: Optional[str] = Field(None, description="Batch ID for progress tracking")
    results: List[Dict[str, Any]] = Field(default_factory=list)


__all__ = [
    "TextExtractionProgress",
    "TextExtractionServiceInfo",
    "TextExtractionHealth",
    "TextExtractionRequest",
    "TextExtractionResponse",
]
