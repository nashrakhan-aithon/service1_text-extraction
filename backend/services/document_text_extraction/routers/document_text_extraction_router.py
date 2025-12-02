from __future__ import annotations

import asyncio
import logging
import threading
from fastapi import APIRouter, HTTPException, BackgroundTasks

from backend.services.document_text_extraction.models import (
    TextExtractionHealth,
    TextExtractionProgress,
    TextExtractionServiceInfo,
    TextExtractionRequest,
    TextExtractionResponse,
)
from backend.services.document_text_extraction.services import (
    DocumentTextExtractionService,
    get_progress_tracker,
)

logger = logging.getLogger(__name__)

# Create service instance
text_extraction_service = DocumentTextExtractionService()

document_text_extraction_router = APIRouter(
    prefix="/document-text-extraction",
    tags=["Document Text Extraction Service (Service 1)"],
    responses={404: {"description": "Document text extraction resource not found"}},
)


@document_text_extraction_router.get("/", response_model=TextExtractionServiceInfo)
async def document_text_extraction_root() -> TextExtractionServiceInfo:
    """Root endpoint describing the document text extraction service (Service 1)."""
    return TextExtractionServiceInfo(
        service="Document Text Extraction Service (Service 1)",
        version="1.0.0",
        status="operational",
        description="Extracts text from PDFs and saves .md files. Embedding and classification handled by Service 2.",
        service_first_architecture=True,
        available_endpoints={
            "service_root": "/document-text-extraction/",
            "service_health": "/document-text-extraction/health",
            "progress": "/document-text-extraction/progress/{batch_id}",
            "api_documentation": "/api/docs",
        },
    )


@document_text_extraction_router.get("/health", response_model=TextExtractionHealth)
async def document_text_extraction_health() -> TextExtractionHealth:
    """Health check for the document text extraction service (Service 1)."""
    return TextExtractionHealth(
        service="document_text_extraction",
        status="healthy",
        capabilities=[
            "pdf_download",
            "ocr_and_text_extraction",
            "text_file_storage",
        ],
    )


@document_text_extraction_router.get(
    "/progress/{batch_id}",
    response_model=TextExtractionProgress,
)
async def get_document_text_extraction_progress(batch_id: str) -> TextExtractionProgress:
    """
    Get real-time progress for an active text extraction batch.

    Returns progress information for Service 1 (text extraction only).
    """
    tracker = get_progress_tracker()
    progress = tracker.get_progress(batch_id)

    if not progress:
        # Instead of raising 404, return completed state to stop polling gracefully
        return TextExtractionProgress(
            batch_id=batch_id,
            status="completed",
            total_documents=0,
            processed_documents=0,
            total_pages=0,
            processed_pages=0,
            progress_percentage=100,
            current_document=None,
            current_stage="completed",
            current_operation="Text extraction completed",
            started_at=None,
            completed_at=None,
            results=[],
            errors=[],
        )

    return TextExtractionProgress(**progress)


@document_text_extraction_router.post(
    "/extract",
    response_model=TextExtractionResponse,
)
async def extract_text(
    request: TextExtractionRequest,
    background_tasks: BackgroundTasks,
) -> TextExtractionResponse:
    """
    Extract text from PDFs for selected queue items (Service 1).
    
    This endpoint:
    1. Extracts text from PDF pages (PyMuPDF/OCR)
    2. Saves .md files to datalake
    3. Updates text_extraction_status = 100
    4. Updates datalake_text_uri
    5. Returns immediately - does NOT wait for embedding/classification
    
    Embedding and classification are handled by Service 2.
    """
    try:
        logger.info(f"Text extraction requested for queue items: {request.queue_ids}")

        # Get progress tracker
        tracker = get_progress_tracker()

        # Start progress tracking
        batch_id = request.batch_id or tracker.start_extraction(request.queue_ids)
        logger.info(f"Started progress tracking for batch {batch_id}")

        # Run text extraction in background
        def run_extraction():
            """Run extraction in background thread."""
            try:
                # Create new event loop for this thread
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

                # Run extraction
                result = loop.run_until_complete(
                    text_extraction_service.extract_text_for_documents(
                        request.queue_ids, batch_id
                    )
                )
                loop.close()

                logger.info(f"Background extraction completed for batch {batch_id}")
                return result
            except Exception as e:
                logger.error(f"Error in background extraction: {str(e)}", exc_info=True)
                return {
                    "success": False,
                    "message": f"Extraction failed: {str(e)}",
                    "results": [],
                    "successful_count": 0,
                    "failed_count": len(request.queue_ids),
                }

        # Start background thread
        thread = threading.Thread(target=run_extraction, daemon=True)
        thread.start()

        # Return immediately with batch_id
        return TextExtractionResponse(
            success=True,
            message=f"Text extraction started for {len(request.queue_ids)} documents",
            processed_count=0,  # Will be updated via progress endpoint
            failed_count=0,
            batch_id=batch_id,
            results=[],
        )

    except Exception as e:
        logger.error(f"Error starting text extraction: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to start text extraction: {str(e)}")


__all__ = ["document_text_extraction_router"]

