"""Common types and data models for Aithon Core SDK."""

from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class ProcessingStatus(Enum):
    """Status of document processing."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class FileType(Enum):
    """Supported file types."""

    PDF = "pdf"
    IMAGE = "image"
    TEXT = "text"
    CSV = "csv"
    JSON = "json"


@dataclass
class PDFInfo:
    """Information about a PDF file."""

    filename: str
    path: str
    size: int
    modified_date: datetime
    page_count: Optional[int] = None
    processing_status: ProcessingStatus = ProcessingStatus.PENDING

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses."""
        return {
            "filename": self.filename,
            "path": self.path,
            "size": self.size,
            "modified_date": self.modified_date.isoformat(),
            "page_count": self.page_count,
            "processing_status": self.processing_status.value,
        }


@dataclass
class ProcessedDocument:
    """Information about a processed document."""

    name: str
    output_folder: str
    processing_date: Optional[datetime] = None
    page_count: Optional[int] = None
    classification_results: Optional[Dict[str, Any]] = None
    extraction_files: List[str] = None
    thumbnails: List[str] = None

    def __post_init__(self):
        if self.extraction_files is None:
            self.extraction_files = []
        if self.thumbnails is None:
            self.thumbnails = []


@dataclass
class ExtractedContent:
    """Content extracted from a document."""

    page_num: int
    text: str
    confidence: float
    extraction_method: str
    processing_time: float
    metadata: Optional[Dict[str, Any]] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


@dataclass
class FileSearchCriteria:
    """Criteria for file searching."""

    file_types: List[FileType]
    max_size: Optional[int] = None
    min_size: Optional[int] = None
    modified_after: Optional[datetime] = None
    modified_before: Optional[datetime] = None
    name_pattern: Optional[str] = None


@dataclass
class PathConfig:
    """Configuration for file paths."""

    data_folders: List[str]
    output_folder: str
    temp_folder: Optional[str] = None
    cache_folder: Optional[str] = None

    def __post_init__(self):
        # Ensure all paths exist or can be created
        from pathlib import Path

        for folder in [self.output_folder] + self.data_folders:
            if folder:
                Path(folder).mkdir(parents=True, exist_ok=True)
