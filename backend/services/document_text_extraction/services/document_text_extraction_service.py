"""
Document Text Extraction Service (Service 1)
============================================

Service 1: Extracts text from PDFs and saves .md files to datalake.
This service ONLY handles text extraction - embedding and classification are handled by Service 2.

Responsibilities:
1. Extract text from PDF pages (PyMuPDF/OCR)
2. Save extracted text as .md files to datalake
3. Update text_extraction_status to 100 (complete)
4. Update datalake_text_uri with path to extracted text folder
5. IMMEDIATELY MOVE TO NEXT PDF - Does NOT wait for embeddings/classification

Implements the text extraction portion of specs-document-text-extraction.md.
"""

# ruff: noqa: E402

from aithon_imports import setup_imports

setup_imports()

import asyncio
import json
import logging
import math
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from backend.core.config import ConfigManager, DatabaseManager
import configparser
from backend.services.document_processing.utils.pdf_processor import PDFProcessor
from backend.services.document_processing.services.file_management_service import (
    FileManagementService,
)

try:
    import boto3
    from botocore.exceptions import BotoCoreError, ClientError
except ImportError:  # pragma: no cover - boto3 is optional until S3 is enabled
    boto3 = None
    BotoCoreError = ClientError = Exception

try:
    import httpx
except ImportError:  # pragma: no cover - httpx is optional until Service 2 integration is enabled
    httpx = None
# Note: Service 1 does NOT use StatusCalculationService or StatusLoggingService
# These services connect to the main database, which Service 1 does NOT touch

from .progress_tracker import progress_tracker


logger = logging.getLogger(__name__)


class DocumentTextExtractionService:
    """
    Service 1: Document Text Extraction Service
    
    Extracts text from PDFs and saves .md files. Does NOT generate embeddings or classify documents.
    Those operations are handled by Service 2 (Document Embedding & Classification Service).
    """

    def __init__(self, default_password: Optional[str] = None):
        """
        Initialize document text extraction service.
        
        Service 1 is COMPLETELY INDEPENDENT:
        - Uses its own .envvar-service1 file
        - Uses its own database (fcr001-text-extraction)
        - Does NOT depend on any existing services or files
        """
        # Service 1 uses its own config file (.envvar-service1)
        # Find project root and use .envvar-service1 instead of .envvar
        # Go up from: backend/services/document_text_extraction/services/
        # To: framev3/ (project root)
        current_file = Path(__file__).resolve()
        # Go up: services/ -> document_text_extraction/ -> services/ -> backend/ -> framev3/
        project_root = current_file.parent.parent.parent.parent
        service1_env_path = project_root / ".envvar-service1"
        
        # Verify file exists
        if not service1_env_path.exists():
            # Try alternative path (in case structure is different)
            alt_path = Path.cwd() / ".envvar-service1"
            if alt_path.exists():
                service1_env_path = alt_path
                logger.info(f"Using Service 1 config from: {service1_env_path}")
            else:
                logger.warning(f"Service 1 config file not found at: {service1_env_path}")
                logger.warning(f"Also tried: {alt_path}")
                logger.warning("Service 1 will use fallback values")
        
        # Create Service 1 ConfigManager with custom env file
        self.config = self._create_service1_config_manager(service1_env_path)
        
        # Get Service 1 database configuration from its own config file
        service1_db_config = {
            "host": self.config.get_var(
                "G_POSTGRES_SERVICE1_HOST", section="POSTGRES_SERVICE1", fallback="localhost"
            ),
            "database": self.config.get_var(
                "G_POSTGRES_SERVICE1_DATABASE", section="POSTGRES_SERVICE1", fallback="fcr001-text-extraction"
            ),
            "user": self.config.get_var(
                "G_POSTGRES_SERVICE1_USER", section="POSTGRES_SERVICE1", fallback="postgres"
            ),
            "password": self.config.get_var(
                "G_POSTGRES_SERVICE1_PASSWORD", section="POSTGRES_SERVICE1", fallback="postgres"
            ),
            "port": self.config.get_var(
                "G_POSTGRES_SERVICE1_PORT", section="POSTGRES_SERVICE1", fallback="5432"
            ),
        }
        
        # Initialize database manager with Service 1 database config
        self.db_manager = DatabaseManager(config=service1_db_config)
        logger.info(f"Service 1 initialized with separate database: {service1_db_config['database']}")
        logger.info(f"Service 1 using config file: {service1_env_path}")

        # Get configuration paths from Service 1's own config file
        # Datalake path (for reading source PDFs)
        self.datalake_path = Path(
            self.config.get_var(
                "G_AITHON_DATALAKE",
                section="COMMON",
                fallback="~/projects/aithon/aithon_output/datalake-fcr001",
            )
        ).expanduser()
        
        # Determine output storage (local filesystem or S3)
        raw_output_folder = self.config.get_var(
            "G_SERVICE1_OUTPUT_FOLDER",
            section="COMMON",
            fallback="~/projects/aithon/aithon_output/service1-extracted-text",
        )

        self.storage_backend = "local"
        self.s3_bucket: Optional[str] = None
        self.s3_prefix: Optional[str] = None
        self.s3_client = None

        if raw_output_folder and str(raw_output_folder).lower().startswith("s3://"):
            if not boto3:
                raise RuntimeError(
                    "boto3 is required for S3 output but is not installed. "
                    "Ensure boto3 is included in requirements."
                )
            self.storage_backend = "s3"
            self.s3_bucket, self.s3_prefix = self._parse_s3_uri(str(raw_output_folder))
            self.s3_client = boto3.client("s3")
            self.service1_output_folder = None
            logger.info(
                "Service 1 will save extracted text to S3: s3://%s/%s",
                self.s3_bucket,
                self.s3_prefix or "",
            )
        else:
            # Default to local filesystem storage
            self.service1_output_folder = Path(str(raw_output_folder)).expanduser()
            self.service1_output_folder.mkdir(parents=True, exist_ok=True)
            logger.info(f"Service 1 will save extracted text to: {self.service1_output_folder}")

        # Initialize services
        # IMPORTANT: Extract ALL pages for UI/storage
        # - max_pages=None: Extract ALL pages for UI display and storage
        # - min_text_length=250: Match training - minimum ~50 words per page
        # If fitz text is garbage or < 250 chars, automatically falls back to Tesseract OCR
        # Note: Embedding generation (Service 2) will use only first 50 pages when reading .md files
        self.pdf_processor = PDFProcessor(
            max_pages=None,         # Extract ALL pages for UI/storage
            min_text_length=250,    # Match training: min ~50 words (250 chars)
            verbose=True
        )
        # Get default password from Service 1's own config
        service1_password = default_password or self.config.get_var(
            "G_DEFAULT_PDF_PWD",
            section="COMMON",
            fallback="operations@PRI"
        )
        self.file_management_service = FileManagementService(default_password=service1_password)
        
        # Note: Service 1 does NOT use StatusCalculationService or StatusLoggingService
        # These services connect to the main database, which Service 1 does NOT touch
        # Service 1 manages its own processing locks in its own database

        # Initialize Service 2 integration (optional)
        self.service2_enabled = self.config.get_var(
            "G_SERVICE2_ENABLED",
            section="COMMON",
            fallback="false"
        ).lower() == "true"
        
        self.service2_http_client = None
        if self.service2_enabled:
            if not httpx:
                logger.warning("Service 2 integration enabled but httpx is not installed. Service 2 calls will be skipped.")
                self.service2_enabled = False
            else:
                self.service2_base_url = self.config.get_var(
                    "G_SERVICE2_BASE_URL",
                    section="COMMON",
                    fallback="http://localhost:8006"
                )
                self.service2_endpoint = self.config.get_var(
                    "G_SERVICE2_ENDPOINT",
                    section="COMMON",
                    fallback="/api/document-classification/classify"
                )
                self.service2_timeout = int(self.config.get_var(
                    "G_SERVICE2_TIMEOUT",
                    section="COMMON",
                    fallback="30"
                ))
                logger.info(f"Service 2 integration enabled: {self.service2_base_url}{self.service2_endpoint}")
        else:
            logger.info("Service 2 integration disabled")

        # Thread pool for parallel processing
        self.thread_pool = ThreadPoolExecutor(max_workers=4)

    async def extract_text_for_documents(
        self, queue_ids: List[int], batch_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Extract text for multiple documents in parallel.

        Args:
            queue_ids: List of queue item IDs to process
            batch_id: Optional batch ID for progress tracking

        Returns:
            Dictionary containing processing results
        """
        logger.info(f"Starting text extraction for {len(queue_ids)} documents")

        # Start progress tracking if batch_id provided
        if batch_id:
            tracker = progress_tracker
            tracker.update_progress(
                batch_id,
                status="processing",
                current_stage="initializing",
                current_operation="Preparing text extraction service...",
                progress_percentage=0,
            )

        # Get document information from queue
        documents = await self._get_documents_from_queue(queue_ids)
        if not documents:
            if batch_id:
                tracker = progress_tracker
                tracker.fail_extraction(batch_id, "No documents found in queue")
            return {
                "success": False,
                "message": "No documents found in queue",
                "results": [],
            }

        # Calculate total pages upfront for accurate progress tracking (0-100%)
        total_pages_upfront = sum(doc.get("number_of_pages", 0) for doc in documents)
        logger.info(f"Total pages to extract: {total_pages_upfront} across {len(documents)} documents")

        # Update progress to show documents found and initialize total_pages
        if batch_id:
            tracker = progress_tracker
            tracker.update_progress(
                batch_id,
                current_stage="initializing",
                current_operation=f"Found {len(documents)} documents ({total_pages_upfront} pages) to process...",
                progress_percentage=0,
                total_pages=total_pages_upfront,  # Initialize total pages upfront
                processed_pages=0,
            )

        # Process documents in parallel
        results = []
        tasks = []

        # Update progress to show processing is starting
        if batch_id:
            tracker = progress_tracker
            tracker.update_progress(
                batch_id,
                current_stage="initializing",
                current_operation="Starting parallel document processing...",
                progress_percentage=10,
            )

        for doc_info in documents:
            task = asyncio.create_task(
                self._process_single_document(doc_info, batch_id)
            )
            tasks.append(task)

        # Wait for all tasks to complete
        completed_tasks = await asyncio.gather(*tasks, return_exceptions=True)

        # Process results
        total_pages_accumulated = 0
        processed_pages_accumulated = 0
        
        for i, result in enumerate(completed_tasks):
            if isinstance(result, Exception):
                logger.error(f"Error processing document {i}: {str(result)}")
                results.append(
                    {
                        "doc_id": documents[i]["doc_id"],
                        "success": False,
                        "error": str(result),
                    }
                )
            else:
                results.append(result)
                
                # Accumulate page counts from successful results
                if result.get("success") and "total_pages" in result:
                    total_pages_accumulated += result.get("total_pages", 0)
                    processed_pages_accumulated += result.get("processed_pages", 0)

            # Progress counter is updated in real-time inside _process_single_document
            if batch_id and i == len(completed_tasks) - 1:
                tracker = progress_tracker
                tracker.update_progress(
                    batch_id,
                    current_stage="completed",
                    total_pages=total_pages_accumulated,
                    processed_pages=processed_pages_accumulated,
                )

        # Count successful vs failed
        successful = sum(1 for r in results if r.get("success", False))
        failed = len(results) - successful

        logger.info(
            f"Text extraction completed: {successful} successful, {failed} failed"
        )
        logger.info(f"Results structure: {[{'doc_id': r.get('doc_id'), 'success': r.get('success')} for r in results]}")

        # Complete progress tracking
        if batch_id:
            tracker = progress_tracker
            if successful > 0:
                logger.info(f"Calling complete_extraction for batch {batch_id} with {successful} successful documents")
                tracker.complete_extraction(batch_id, results)
            else:
                logger.warning(f"Calling fail_extraction for batch {batch_id} - all {len(results)} documents failed")
                tracker.fail_extraction(batch_id, "All documents failed to process")

        return {
            "success": successful > 0,
            "message": f"Processed {len(results)} documents: {successful} successful, {failed} failed",
            "results": results,
            "successful_count": successful,
            "failed_count": failed,
        }

    async def _get_documents_from_queue(
        self, queue_ids: List[int]
    ) -> List[Dict[str, Any]]:
        """
        Get document information from Service 1's own database.
        
        Note: queue_ids here refer to extraction_id in doc_text_extraction_queue table.
        """
        try:
            with self.db_manager.get_connection() as conn:
                with conn.cursor() as cursor:
                    query = """
                        SELECT extraction_id, doc_id, doc_name, file_ext, source_uri, 
                               datalake_raw_uri, password, text_extraction_status, number_of_pages
                        FROM doc_text_extraction_queue 
                        WHERE extraction_id = ANY(%s) AND is_active = true
                    """

                    cursor.execute(query, (queue_ids,))
                    results = cursor.fetchall()

                    documents = []
                    for row in results:
                        documents.append(
                            {
                                "extraction_id": row[0],  # extraction_id instead of queue_id
                                "doc_id": row[1],
                                "doc_name": row[2],
                                "file_ext": row[3],
                                "source_uri": row[4],
                                "datalake_raw_uri": row[5],
                                "password": row[6],
                                "text_extraction_status": row[7],
                                "number_of_pages": row[8],
                            }
                        )

                    return documents

        except Exception as e:
            logger.error(f"Error getting documents from Service 1 queue: {str(e)}")
            return []

    async def _process_single_document(
        self, doc_info: Dict[str, Any], batch_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Process a single document through the text extraction pipeline.
        
        Service 1 ONLY: Extracts text and saves .md files. Stops here.
        Embedding and classification are handled by Service 2.

        Args:
            doc_info: Document information from queue
            batch_id: Optional batch ID for progress tracking

        Returns:
            Processing result dictionary
        """
        doc_id = doc_info["doc_id"]
        logger.info(f"Processing document: {doc_id}")

        # Start timing the text extraction process
        start_time = time.time()
        lock_acquired = False

        try:
            # Set processing lock in Service 1's own database
            lock_acquired = await self._set_processing_lock(doc_id)
            if not lock_acquired:
                logger.warning(f"Document {doc_id} is already being processed")
                return {
                    "doc_id": doc_id,
                    "success": False,
                    "error": "Document is currently being processed",
                }

            # Update progress
            if batch_id:
                tracker = progress_tracker
                tracker.update_progress(
                    batch_id,
                    current_document=doc_id,
                    current_stage="downloading_pdf",
                    current_operation="Accessing PDF file from datalake",
                    status="processing",
                )

            # Step 1: Download/access PDF file
            pdf_path = await self._get_pdf_file(doc_info)
            if not pdf_path:
                await self._update_queue_status(
                    doc_id, "text_extraction_status", -1
                )  # -1 = failed
                await self._update_error_message(doc_id, "Could not access PDF file")
                return {
                    "doc_id": doc_id,
                    "success": False,
                    "error": "Could not access PDF file",
                }

            # Note: Service 1 doesn't track download_status (that's in main database)
            # Service 1 only tracks text_extraction_status

            # Update datalake_raw_uri in database
            await self._update_datalake_raw_uri(doc_id, str(pdf_path))

            # Update progress
            if batch_id:
                tracker = progress_tracker
                tracker.update_progress(
                    batch_id,
                    current_document=doc_id,
                    current_stage="extracting_text",
                    current_operation="Extracting text from PDF pages using PyMuPDF/OCR",
                    status="processing",
                )

            # Step 2: Extract text from PDF
            extraction_result = await self._extract_pdf_text(
                pdf_path, doc_info.get("password")
            )
            if not extraction_result["success"]:
                await self._update_queue_status(
                    doc_id, "text_extraction_status", -1
                )  # -1 = failed
                error_msg = extraction_result.get("error_message", "PDF extraction failed")
                await self._update_error_message(doc_id, error_msg)
                return {
                    "doc_id": doc_id,
                    "success": False,
                    "error": error_msg,
                }

            # Step 3: Save extracted content to Service 1's own output folder (local or S3)
            file_paths = self._save_extracted_content_to_service1_folder(
                doc_id, extraction_result
            )

            # Update datalake_text_uri in database (points to Service 1's output folder)
            if self.storage_backend == "s3":
                service1_text_path = f"s3://{self.s3_bucket}/{self._build_s3_output_prefix(doc_id)}"
            else:
                service1_text_path = self.service1_output_folder / doc_id / "extracted_text"

            await self._update_datalake_text_uri(doc_id, str(service1_text_path))
            
            # Set text_extraction_status to 100 (complete)
            # All pages extracted and saved to .md files
            await self._update_queue_status(
                doc_id, "text_extraction_status", 100
            )

            # Update progress - text extraction complete
            if batch_id:
                tracker = progress_tracker
                tracker.update_progress(
                    batch_id,
                    current_document=doc_id,
                    current_stage="completed",
                    current_operation="Text extraction completed - ready for Service 2 (embedding/classification)",
                    status="completed",
                )

            # ✅ SERVICE 1 COMPLETE - Text extraction done
            # Embedding and classification will be handled by Service 2
            # Service 1 immediately moves to next PDF without waiting
            status = "success"
            
            logger.info(
                f"✅ Service 1 complete for {doc_id}: Text extracted and saved. "
                f"Ready for Service 2 (embedding/classification)."
            )

            # Calculate and save duration
            end_time = time.time()
            duration_seconds = int(end_time - start_time)
            logger.info(
                f"Calculated duration for {doc_id}: {duration_seconds} seconds (start: {start_time}, end: {end_time})"
            )
            await self._update_text_extraction_duration(doc_id, duration_seconds)

            # Update last processed timestamp
            await self._update_last_processed(doc_id)

            logger.info(
                f"Completed processing document {doc_id}: {status} (Duration: {duration_seconds}s)"
            )

            # Call Service 2 (Document Embedding & Classification) after successful extraction
            extraction_id = doc_info.get("extraction_id")
            if extraction_id:
                service2_success = await self._call_service2(extraction_id, doc_id)
                if service2_success:
                    logger.info(f"Service 2 called successfully for extraction_id={extraction_id}")
                else:
                    logger.warning(
                        f"Service 2 call failed for extraction_id={extraction_id}, "
                        f"but text extraction completed successfully"
                    )
            else:
                logger.warning(f"Could not call Service 2: extraction_id not found in doc_info for {doc_id}")

            # Increment processed count IMMEDIATELY after document completes
            total_pages = extraction_result["total_pages"]
            processed_pages = total_pages  # All pages were processed, regardless of text content
            
            if batch_id:
                tracker = progress_tracker
                processed_count = tracker.increment_processed(batch_id, processed_pages=processed_pages)
                logger.info(f"Updated progress: {processed_count} documents completed ({processed_pages}/{total_pages} pages)")

            return {
                "doc_id": doc_id,
                "success": True,
                "status": status,
                "total_pages": total_pages,
                "processed_pages": processed_pages,
                "file_paths": file_paths,
                "duration_seconds": duration_seconds,
            }

        except Exception as e:
            logger.error(f"Error processing document {doc_id}: {str(e)}", exc_info=True)
            
            # Update status to failed (-1) and log error
            await self._update_queue_status(
                doc_id, "text_extraction_status", -1
            )  # -1 = failed
            
            # Store error message
            await self._update_error_message(doc_id, str(e))
            
            # Increment processed count even on failure
            if batch_id:
                tracker = progress_tracker
                processed_count = tracker.increment_processed(batch_id)
                logger.info(f"Updated progress (with error): {processed_count} documents completed")
            
            return {"doc_id": doc_id, "success": False, "error": str(e)}
        finally:
            # Always clear processing lock, even on early returns or exceptions
            if lock_acquired:
                await self._clear_processing_lock(doc_id)

    async def _get_pdf_file(self, doc_info: Dict[str, Any]) -> Optional[str]:
        """Get PDF file using file management service."""
        return await self.file_management_service.get_pdf_file(doc_info)

    async def _extract_pdf_text(
        self, pdf_path: str, password: Optional[str] = None
    ) -> Dict[str, Any]:
        """Extract text from PDF using enhanced PDF processor with smart password handling."""
        try:
            # Run enhanced PDF processing in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                self.thread_pool,
                self.pdf_processor.extract_text_from_pdf_enhanced,
                pdf_path,
                password,
                self.file_management_service,  # Pass file management service
            )
            return result
        except Exception as e:
            logger.error(f"Error extracting PDF text: {str(e)}")
            return {"success": False, "error_message": str(e), "password_required": False}

    def _save_extracted_content_to_service1_folder(
        self, doc_id: str, extraction_result: Dict[str, Any]
    ) -> Dict[int, Dict[str, str]]:
        """
        Save extracted text to Service 1's output destination.
        
        When G_SERVICE1_OUTPUT_FOLDER points to an S3 URI, files are uploaded to S3.
        Otherwise, they are written to the local filesystem (existing behavior).
        """
        if self.storage_backend == "s3":
            return self._save_extracted_content_to_s3(doc_id, extraction_result)

        # Local filesystem storage
        doc_folder = self.service1_output_folder / doc_id
        doc_folder.mkdir(parents=True, exist_ok=True)

        extracted_text_dir = doc_folder / "extracted_text"
        extracted_text_dir.mkdir(exist_ok=True)

        file_paths: Dict[int, Dict[str, str]] = {}

        for page_num, page_data in extraction_result["pages"].items():
            method = page_data["method"]
            text = page_data["text"]

            text_file = extracted_text_dir / f"page_{page_num:04d}_{method}.md"
            with open(text_file, "w", encoding="utf-8") as f:
                f.write(f"# Page {page_num} - {method.upper()}\n\n")
                f.write(text)

            file_paths[page_num] = {
                "text_file": str(text_file),
            }

        logger.info(
            "Saved extracted text for %s to Service 1 output folder: %s",
            doc_id,
            extracted_text_dir,
        )
        return file_paths

    def _save_extracted_content_to_s3(
        self, doc_id: str, extraction_result: Dict[str, Any]
    ) -> Dict[int, Dict[str, str]]:
        """Upload extracted text pages to S3."""
        if not self.s3_client or not self.s3_bucket:
            raise RuntimeError("S3 client is not configured but storage_backend is set to 's3'")

        file_paths: Dict[int, Dict[str, str]] = {}
        base_prefix = self._build_s3_output_prefix(doc_id)

        for page_num, page_data in extraction_result["pages"].items():
            method = page_data["method"]
            text = page_data["text"]
            key = f"{base_prefix}/page_{page_num:04d}_{method}.md"
            body = f"# Page {page_num} - {method.upper()}\n\n{text}".encode("utf-8")

            try:
                self.s3_client.put_object(
                    Bucket=self.s3_bucket,
                    Key=key,
                    Body=body,
                    ContentType="text/markdown; charset=utf-8",
                )
            except (BotoCoreError, ClientError) as s3_error:
                logger.error(
                    "Failed to upload page %s for %s to S3: %s",
                    page_num,
                    doc_id,
                    str(s3_error),
                )
                raise

            file_paths[page_num] = {
                "text_file": f"s3://{self.s3_bucket}/{key}",
            }

        logger.info(
            "Saved extracted text for %s to S3 location: s3://%s/%s",
            doc_id,
            self.s3_bucket,
            base_prefix,
        )
        return file_paths

    async def _update_queue_status(
        self, doc_id: str, status_field: str, status_value: int
    ) -> bool:
        """Update queue status for a document in Service 1's own database."""
        try:
            with self.db_manager.get_connection() as conn:
                with conn.cursor() as cursor:
                    query = f"""
                        UPDATE doc_text_extraction_queue 
                        SET {status_field} = %s, updated_at = now()
                        WHERE doc_id = %s
                    """

                    cursor.execute(query, (status_value, doc_id))
                    conn.commit()

                    logger.info(
                        f"Updated {status_field} to {status_value} for document {doc_id} in Service 1 database"
                    )
                    return True

        except Exception as e:
            logger.error(f"Error updating queue status: {str(e)}")
            return False

    async def _update_text_extraction_duration(
        self, doc_id: str, duration_seconds: int
    ) -> bool:
        """Update text extraction duration in Service 1's own database."""
        try:
            with self.db_manager.get_connection() as conn:
                with conn.cursor() as cursor:
                    query = """
                        UPDATE doc_text_extraction_queue 
                        SET text_extraction_duration_seconds = %s, updated_at = now()
                        WHERE doc_id = %s
                    """

                    cursor.execute(query, (duration_seconds, doc_id))
                    conn.commit()

                    logger.info(
                        f"Updated text_extraction_duration_seconds to {duration_seconds} for document {doc_id}"
                    )
                    return True

        except Exception as e:
            logger.error(f"Error updating text extraction duration: {str(e)}")
            return False

    async def _update_last_processed(self, doc_id: str) -> bool:
        """Update last processed timestamp in Service 1's own database."""
        try:
            with self.db_manager.get_connection() as conn:
                with conn.cursor() as cursor:
                    query = """
                        UPDATE doc_text_extraction_queue 
                        SET last_processed_at = now(), updated_at = now(), extracted_at = now()
                        WHERE doc_id = %s
                    """

                    cursor.execute(query, (doc_id,))
                    conn.commit()

                    return True

        except Exception as e:
            logger.error(f"Error updating last processed timestamp: {str(e)}")
            return False

    async def _update_datalake_raw_uri(self, doc_id: str, raw_uri: str) -> bool:
        """Update datalake_raw_uri in Service 1's own database."""
        try:
            with self.db_manager.get_connection() as conn:
                with conn.cursor() as cursor:
                    query = """
                        UPDATE doc_text_extraction_queue 
                        SET datalake_raw_uri = %s, updated_at = now()
                        WHERE doc_id = %s
                    """

                    cursor.execute(query, (raw_uri, doc_id))
                    conn.commit()

                    logger.info(f"Updated datalake_raw_uri for {doc_id}: {raw_uri}")
                    return True

        except Exception as e:
            logger.error(f"Error updating datalake_raw_uri: {str(e)}")
            return False

    async def _update_datalake_text_uri(self, doc_id: str, text_uri: str) -> bool:
        """Update datalake_text_uri in Service 1's own database."""
        try:
            with self.db_manager.get_connection() as conn:
                with conn.cursor() as cursor:
                    query = """
                        UPDATE doc_text_extraction_queue 
                        SET datalake_text_uri = %s, updated_at = now()
                        WHERE doc_id = %s
                    """

                    cursor.execute(query, (text_uri, doc_id))
                    conn.commit()

                    logger.info(f"Updated datalake_text_uri for {doc_id}: {text_uri}")
                    return True

        except Exception as e:
            logger.error(f"Error updating datalake_text_uri: {str(e)}")
            return False

    async def _update_error_message(self, doc_id: str, error_message: str) -> bool:
        """Update last_error_message in Service 1's own database."""
        try:
            with self.db_manager.get_connection() as conn:
                with conn.cursor() as cursor:
                    query = """
                        UPDATE doc_text_extraction_queue 
                        SET last_error_message = %s, error_message = %s, updated_at = now()
                        WHERE doc_id = %s
                    """

                    cursor.execute(query, (error_message, error_message, doc_id))
                    conn.commit()

                    logger.info(f"Updated error message for {doc_id}")
                    return True

        except Exception as e:
            logger.error(f"Error updating error message: {str(e)}")
            return False

    async def _call_service2(self, extraction_id: int, doc_id: str) -> bool:
        """
        Call Service 2 (Document Embedding & Classification) after successful text extraction.
        
        Args:
            extraction_id: The extraction_id from doc_text_extraction_queue
            doc_id: The document ID
            
        Returns:
            True if Service 2 call was successful or disabled, False if call failed
        """
        if not self.service2_enabled or not httpx:
            logger.debug(f"Service 2 integration disabled, skipping call for extraction_id={extraction_id}")
            return True
        
        try:
            service2_url = f"{self.service2_base_url}{self.service2_endpoint}"
            payload = {
                "extraction_ids": [extraction_id]
            }
            
            logger.info(f"Calling Service 2 for extraction_id={extraction_id}, doc_id={doc_id}")
            logger.info(f"Service 2 URL: {service2_url}, Payload: {payload}")
            
            async with httpx.AsyncClient(timeout=self.service2_timeout) as client:
                response = await client.post(
                    service2_url,
                    json=payload,
                    timeout=self.service2_timeout
                )
            
            if response.status_code in (200, 201, 202):
                response_summary: str
                try:
                    response_json = response.json()
                    response_summary = json.dumps(response_json, indent=2)[:1000]
                except Exception:
                    response_summary = response.text[:1000]

                logger.info(
                    f"✅ Successfully called Service 2 for extraction_id={extraction_id}, "
                    f"doc_id={doc_id}. Status: {response.status_code}"
                )
                logger.info(
                    "Service 2 response preview (truncated to 1KB):\n%s",
                    response_summary,
                )
                return True
            else:
                logger.warning(
                    f"Service 2 returned non-success status {response.status_code} for "
                    f"extraction_id={extraction_id}, doc_id={doc_id}. Response: {response.text[:200]}"
                )
                return False
                
        except httpx.TimeoutException:
            logger.error(
                f"Timeout calling Service 2 for extraction_id={extraction_id}, "
                f"doc_id={doc_id} (timeout: {self.service2_timeout}s)"
            )
            return False
        except httpx.RequestError as e:
            logger.error(
                f"Request error calling Service 2 for extraction_id={extraction_id}, "
                f"doc_id={doc_id}: {str(e)}"
            )
            return False
        except Exception as e:
            logger.error(
                f"Unexpected error calling Service 2 for extraction_id={extraction_id}, "
                f"doc_id={doc_id}: {str(e)}",
                exc_info=True
            )
            return False

    async def get_processing_status(self, doc_id: str) -> Dict[str, Any]:
        """Get current processing status for a document from Service 1's own database."""
        try:
            with self.db_manager.get_connection() as conn:
                with conn.cursor() as cursor:
                    query = """
                        SELECT text_extraction_status, error_message, last_processed_at, extracted_at
                        FROM doc_text_extraction_queue 
                        WHERE doc_id = %s
                    """

                    cursor.execute(query, (doc_id,))
                    result = cursor.fetchone()

                    if result:
                        return {
                            "text_extraction_status": result[0],
                            "error_message": result[1],
                            "last_processed_at": result[2],
                            "extracted_at": result[3],
                        }
                    else:
                        return {"error": "Document not found in Service 1 database"}

        except Exception as e:
            logger.error(f"Error getting processing status: {str(e)}")
            return {"error": str(e)}

    async def _set_processing_lock(self, doc_id: str) -> bool:
        """Set processing lock in Service 1's own database."""
        try:
            with self.db_manager.get_connection() as conn:
                with conn.cursor() as cursor:
                    # Check if already processing
                    cursor.execute("""
                        SELECT is_processing FROM doc_text_extraction_queue 
                        WHERE doc_id = %s AND is_processing = TRUE
                    """, (doc_id,))
                    
                    if cursor.fetchone():
                        return False  # Already processing
                    
                    # Set lock
                    cursor.execute("""
                        UPDATE doc_text_extraction_queue 
                        SET is_processing = TRUE, processing_started_at = now(), updated_at = now()
                        WHERE doc_id = %s
                    """, (doc_id,))
                    conn.commit()
                    
                    logger.info(f"Set processing lock for {doc_id} in Service 1 database")
                    return True
        except Exception as e:
            logger.error(f"Error setting processing lock: {str(e)}")
            return False

    async def _clear_processing_lock(self, doc_id: str) -> bool:
        """Clear processing lock in Service 1's own database."""
        try:
            with self.db_manager.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        UPDATE doc_text_extraction_queue 
                        SET is_processing = FALSE, processing_started_at = NULL, updated_at = now()
                        WHERE doc_id = %s
                    """, (doc_id,))
                    conn.commit()
                    
                    logger.info(f"Cleared processing lock for {doc_id} in Service 1 database")
                    return True
        except Exception as e:
            logger.error(f"Error clearing processing lock: {str(e)}")
            return False

    def _create_service1_config_manager(self, env_path: Path) -> ConfigManager:
        """
        Create a ConfigManager instance that reads from Service 1's own .envvar-service1 file.
        
        This allows Service 1 to be completely independent from the main .envvar file.
        """
        # Create a custom ConfigManager that reads from .envvar-service1
        class Service1ConfigManager(ConfigManager):
            def __init__(self, env_path: Path):
                """Initialize with Service 1's config file."""
                import configparser
                self.env_path = env_path
                self.logger = logging.getLogger(__name__)
                self._config = configparser.ConfigParser()
                self._config.optionxform = str
                if self.env_path.exists():
                    self._config.read(self.env_path)
                    self.logger.info(f"Service 1 loaded config from: {self.env_path}")
                else:
                    self.logger.error(f"Service 1 config file not found: {self.env_path}")
                    self.logger.warning("Service 1 will use fallback values")
            
            def get_var(
                self, key: str, section: Optional[str] = None, fallback: Optional[str] = None
            ) -> Optional[str]:
                """Get variable - checks environment variables FIRST, then config file.
                
                This allows docker-compose environment variables to override .envvar-service1.
                Inside Docker container, environment variables are set by docker-compose.
                """
                import os
                # CRITICAL: Check environment variables FIRST (set by docker-compose)
                # This allows docker-compose environment variables to override .envvar-service1
                env_value = os.getenv(key)
                if env_value:
                    return env_value
                
                # Fall back to config file if not in environment
                try:
                    if section:
                        return self._config.get(section, key, fallback=fallback)
                    # Search all sections
                    for sec in self._config.sections():
                        if key in self._config[sec]:
                            return self._config[sec][key]
                    return fallback
                except Exception:
                    return fallback
            
            def get_g_vars(self, section: Optional[str] = None) -> Dict[str, str]:
                """Return G_* variables from Service 1's config."""
                result: Dict[str, str] = {}
                if section:
                    if section in self._config:
                        for k, v in self._config[section].items():
                            if k.startswith("G_"):
                                result[k] = v
                    return result
                # All sections
                for sec in self._config.sections():
                    for k, v in self._config[sec].items():
                        if k.startswith("G_"):
                            result[k] = v
                return result
        
        return Service1ConfigManager(env_path)

    def cleanup(self):
        """Cleanup resources."""
        if hasattr(self, "thread_pool"):
            self.thread_pool.shutdown(wait=True)

    def _parse_s3_uri(self, uri: str) -> Tuple[str, str]:
        """Split an s3://bucket/prefix URI into bucket and prefix components."""
        without_scheme = uri[5:]  # strip "s3://"
        parts = without_scheme.split("/", 1)
        bucket = parts[0]
        prefix = parts[1] if len(parts) > 1 else ""
        return bucket, prefix.strip("/")

    def _build_s3_output_prefix(self, doc_id: str) -> str:
        """Build the base prefix under which extracted files are stored for a document."""
        segments = [segment for segment in [self.s3_prefix, doc_id, "extracted_text"] if segment]
        return "/".join(segments)

