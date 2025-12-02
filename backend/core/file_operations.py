"""File operations for Aithon Core SDK - handles file discovery, path resolution, and status checking."""

import os
import sys
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime
import logging

from .types import (
    PDFInfo,
    ProcessedDocument,
    ProcessingStatus,
    FileSearchCriteria,
    PathConfig,
)

logger = logging.getLogger(__name__)


class FileManager:
    """Centralized file management for all Aithon services."""

    def __init__(self, path_config: PathConfig):
        """Initialize with path configuration."""
        self.path_config = path_config
        self.logger = logging.getLogger(__name__)

    def find_file(self, filename: str) -> Optional[str]:
        """
        Find a file across all configured data folders.

        This consolidates the logic from msb_file_service.py:975-982
        """
        self.logger.info(f"🔍 Looking for file: {filename}")
        self.logger.info(f"🔍 Data folders to search: {self.path_config.data_folders}")

        for data_folder in self.path_config.data_folders:
            if not data_folder:  # Skip empty folder paths
                continue

            potential_path = Path(data_folder) / filename
            self.logger.debug(f"🔍 Checking: {potential_path}")
            self.logger.debug(f"   Exists: {potential_path.exists()}")

            if potential_path.exists():
                found_path = str(potential_path)
                self.logger.info(f"✅ Found file at: {found_path}")
                return found_path

        self.logger.warning(f"❌ File {filename} not found in any data folders")
        return None

    def find_file_or_raise(self, filename: str) -> str:
        """Find file or raise exception if not found."""
        file_path = self.find_file(filename)
        if not file_path:
            raise FileNotFoundError(
                f"File {filename} not found in data folders: {self.path_config.data_folders}"
            )
        return file_path

    def check_file_processed(self, document_name: str, page_num: int) -> bool:
        """
        Check if a specific page has been processed.

        Consolidates logic from msb_file_service.py:828
        """
        try:
            # Get the base filename without extension
            base_name = (
                document_name.replace(".pdf", "")
                if document_name.endswith(".pdf")
                else document_name
            )

            # Construct the expected output file path
            openai_output_dir = os.path.join(
                self.path_config.output_folder, f"{base_name}_openai_output"
            )

            # Check for both regular and AI extraction files (1-based page numbering in filenames)
            regular_file = os.path.join(
                openai_output_dir, f"{base_name}_page_{page_num + 1:04d}.md"
            )
            ai_file = os.path.join(
                openai_output_dir, f"{base_name}_page_{page_num + 1:04d}-ai.md"
            )

            file_exists = os.path.exists(regular_file) or os.path.exists(ai_file)

            if file_exists:
                self.logger.debug(
                    f"✅ Page {page_num + 1} already processed for {document_name}"
                )
            else:
                self.logger.debug(
                    f"⏳ Page {page_num + 1} not yet processed for {document_name}"
                )

            return file_exists

        except Exception as e:
            self.logger.error(
                f"Error checking if page {page_num + 1} is processed for {document_name}: {str(e)}"
            )
            return False

    def get_output_folder(self, document_name: str, subfolder: str = None) -> Path:
        """Get output folder path for a document."""
        base_name = (
            document_name.replace(".pdf", "")
            if document_name.endswith(".pdf")
            else document_name
        )

        if subfolder:
            output_path = (
                Path(self.path_config.output_folder) / f"{base_name}_{subfolder}"
            )
        else:
            output_path = Path(self.path_config.output_folder) / base_name

        output_path.mkdir(parents=True, exist_ok=True)
        return output_path

    def list_files_in_folder(
        self, folder_path: str, file_extension: str = ".pdf"
    ) -> List[Dict[str, Any]]:
        """List files in a folder with metadata."""
        if not os.path.exists(folder_path):
            return []

        files = []
        try:
            for item in os.listdir(folder_path):
                if item.lower().endswith(file_extension.lower()):
                    item_path = os.path.join(folder_path, item)
                    file_stats = os.stat(item_path)

                    files.append(
                        {
                            "filename": item,
                            "path": item_path,
                            "size": file_stats.st_size,
                            "modified_date": datetime.fromtimestamp(
                                file_stats.st_mtime
                            ),
                        }
                    )

        except Exception as e:
            self.logger.error(f"Error reading folder {folder_path}: {str(e)}")

        # Sort by filename alphabetically
        files.sort(key=lambda x: x["filename"])
        return files


class PDFDiscovery:
    """Specialized PDF file discovery and management."""

    def __init__(self, file_manager: FileManager):
        """Initialize with file manager."""
        self.file_manager = file_manager
        self.logger = logging.getLogger(__name__)

    def discover_pdfs(self, folder_path: str) -> List[PDFInfo]:
        """Discover all PDF files in a folder."""
        files_data = self.file_manager.list_files_in_folder(folder_path, ".pdf")

        pdfs = []
        for file_data in files_data:
            # Determine processing status
            status = self._determine_processing_status(file_data["filename"])

            pdf_info = PDFInfo(
                filename=file_data["filename"],
                path=file_data["path"],
                size=file_data["size"],
                modified_date=file_data["modified_date"],
                processing_status=status,
            )
            pdfs.append(pdf_info)

        return pdfs

    def _determine_processing_status(self, filename: str) -> ProcessingStatus:
        """Determine processing status of a PDF file."""
        try:
            # Check if output folder exists for this document
            base_name = (
                filename.replace(".pdf", "") if filename.endswith(".pdf") else filename
            )
            output_folder = (
                Path(self.file_manager.path_config.output_folder)
                / f"{base_name}_extracted_text"
            )

            if output_folder.exists():
                # Check if classification results exist
                classification_file = output_folder / "classification_results.json"
                if classification_file.exists():
                    return ProcessingStatus.COMPLETED
                else:
                    return ProcessingStatus.IN_PROGRESS
            else:
                return ProcessingStatus.PENDING

        except Exception as e:
            self.logger.error(
                f"Error determining processing status for {filename}: {str(e)}"
            )
            return ProcessingStatus.PENDING

    def get_processed_documents(self) -> List[ProcessedDocument]:
        """Get list of all processed documents."""
        if not os.path.exists(self.file_manager.path_config.output_folder):
            return []

        processed_docs = []
        try:
            for item in os.listdir(self.file_manager.path_config.output_folder):
                item_path = os.path.join(
                    self.file_manager.path_config.output_folder, item
                )

                if os.path.isdir(item_path):
                    # Check if this looks like a processed document folder
                    doc_info = self._analyze_processed_folder(item_path, item)
                    if doc_info:
                        processed_docs.append(doc_info)

        except Exception as e:
            self.logger.error(f"Error getting processed documents: {str(e)}")

        return processed_docs

    def _analyze_processed_folder(
        self, folder_path: str, folder_name: str
    ) -> Optional[ProcessedDocument]:
        """Analyze a processed document folder."""
        try:
            doc = ProcessedDocument(name=folder_name, output_folder=folder_path)

            # Look for classification results
            classification_file = os.path.join(
                folder_path, "classification_results.json"
            )
            if os.path.exists(classification_file):
                import json

                with open(classification_file, "r") as f:
                    doc.classification_results = json.load(f)

                # Extract processing date if available
                if (
                    doc.classification_results
                    and "processed_date" in doc.classification_results
                ):
                    try:
                        doc.processing_date = datetime.fromisoformat(
                            doc.classification_results["processed_date"]
                        )
                    except:
                        pass

            # Look for extraction files
            for file in os.listdir(folder_path):
                if file.endswith(".csv"):
                    doc.extraction_files.append(os.path.join(folder_path, file))

            # Look for thumbnails
            possible_thumbnail_dirs = [
                os.path.join(folder_path, "thumbnails"),
                os.path.join(folder_path, "page_images"),
                folder_path,  # Sometimes thumbnails are in main folder
            ]

            for thumbnails_folder in possible_thumbnail_dirs:
                if os.path.exists(thumbnails_folder):
                    thumbnail_files = [
                        f
                        for f in os.listdir(thumbnails_folder)
                        if f.lower().endswith((".png", ".jpg", ".jpeg"))
                    ]
                    if thumbnail_files:
                        doc.thumbnails = sorted(thumbnail_files)
                        break

            # Estimate page count
            if doc.classification_results:
                doc.page_count = len(doc.classification_results.get("pages", {}))
            elif doc.thumbnails:
                doc.page_count = len(doc.thumbnails)

            return doc

        except Exception as e:
            self.logger.error(
                f"Error analyzing processed folder {folder_path}: {str(e)}"
            )
            return None
