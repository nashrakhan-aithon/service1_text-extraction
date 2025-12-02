from __future__ import annotations

import logging
import threading
import time
from datetime import datetime
from typing import Any, Dict, List, Optional


logger = logging.getLogger(__name__)


class ProgressTracker:
    """In-memory progress tracker for text extraction operations."""

    def __init__(self) -> None:
        self._progress_trackers: Dict[str, Dict[str, Any]] = {}
        self._progress_lock = threading.Lock()

    def start_extraction(self, queue_ids: List[int]) -> str:
        """Start tracking progress for a batch of queue items."""
        batch_id = f"batch_{int(time.time())}_{len(queue_ids)}"

        with self._progress_lock:
            self._progress_trackers[batch_id] = {
                "total_documents": len(queue_ids),
                "processed_documents": 0,
                "total_pages": 0,  # Will be updated as we discover page counts
                "processed_pages": 0,
                "current_document": None,
                "current_stage": None,
                "current_operation": None,
                "status": "starting",
                "start_time": time.time() * 1000,  # Unix timestamp in milliseconds
                "last_update": time.time() * 1000,
                "results": [],
                "errors": [],
            }

        logger.info(
            "Started progress tracking for batch %s with %d documents",
            batch_id,
            len(queue_ids),
        )
        return batch_id

    def increment_processed(
        self,
        batch_id: str,
        total_pages: int = 0,
        processed_pages: int = 0,
    ) -> int:
        """Increment processed documents count and update page progress (0-100%)."""
        with self._progress_lock:
            if batch_id not in self._progress_trackers:
                return 0

            tracker = self._progress_trackers[batch_id]
            tracker["processed_documents"] += 1
            count = tracker["processed_documents"]
            total = tracker["total_documents"]

            if processed_pages > 0:
                tracker["processed_pages"] += processed_pages

            if tracker["total_pages"] > 0:
                tracker["progress_percentage"] = int(
                    (tracker["processed_pages"] / tracker["total_pages"]) * 100
                )
            else:
                tracker["progress_percentage"] = (
                    int((count / total) * 100) if total > 0 else 0
                )

            tracker["last_update"] = datetime.now()

            logger.info(
                "Progress update for batch %s: %d/%d documents (%d%%) - Pages: %d/%d",
                batch_id,
                count,
                total,
                tracker.get("progress_percentage", 0),
                tracker["processed_pages"],
                tracker["total_pages"],
            )
            return count

    def update_progress(self, batch_id: str, **kwargs: Any) -> None:
        """Update progress for a batch."""
        with self._progress_lock:
            if batch_id not in self._progress_trackers:
                logger.warning("Batch %s not found in progress trackers", batch_id)
                return

            tracker = self._progress_trackers[batch_id]

            for key, value in kwargs.items():
                if key in tracker:
                    tracker[key] = value

            if "processed_documents" in kwargs and tracker["total_documents"] > 0:
                tracker["progress_percentage"] = int(
                    (tracker["processed_documents"] / tracker["total_documents"]) * 100
                )

            tracker["last_update"] = datetime.now()
            logger.info("Updated progress for batch %s: %s", batch_id, kwargs)

    def get_progress(self, batch_id: str) -> Optional[Dict[str, Any]]:
        """Get current progress for a batch."""
        with self._progress_lock:
            if batch_id not in self._progress_trackers:
                logger.warning("No progress found for batch %s", batch_id)
                return None

            tracker = self._progress_trackers[batch_id]
            progress = {
                "batch_id": batch_id,
                "status": tracker["status"],
                "total_documents": tracker["total_documents"],
                "processed_documents": tracker["processed_documents"],
                "total_pages": tracker.get("total_pages", 0),
                "processed_pages": tracker.get("processed_pages", 0),
                "current_document": tracker["current_document"],
                "current_stage": tracker["current_stage"],
                "current_operation": tracker["current_operation"],
                "progress_percentage": tracker.get("progress_percentage", 0),
                "started_at": tracker["start_time"],
                "completed_at": tracker.get("completed_at", None),
                "results": tracker["results"],
                "errors": tracker["errors"],
                "current_operation_started_at": tracker.get(
                    "current_operation_started_at",
                    None,
                ),
            }

            logger.info(
                "Retrieved progress for batch %s: %s - %d%%",
                batch_id,
                progress.get("status"),
                progress.get("progress_percentage", 0),
            )
            return progress

    def complete_extraction(self, batch_id: str, results: List[Dict[str, Any]]) -> None:
        """Mark extraction as completed."""
        with self._progress_lock:
            if batch_id not in self._progress_trackers:
                logger.warning("Batch %s not found for completion", batch_id)
                return

            tracker = self._progress_trackers[batch_id]
            tracker["status"] = "completed"
            tracker["completed_at"] = time.time() * 1000
            tracker["results"] = results if results else []
            tracker["progress_percentage"] = 100
            tracker["last_update"] = time.time() * 1000

        logger.info("Completed progress tracking for batch %s", batch_id)

        def cleanup_later() -> None:
            time.sleep(300)  # 5 minutes
            with self._progress_lock:
                if batch_id in self._progress_trackers:
                    del self._progress_trackers[batch_id]
                    logger.info("Cleaned up completed batch %s", batch_id)

        cleanup_thread = threading.Thread(target=cleanup_later, daemon=True)
        cleanup_thread.start()

    def fail_extraction(self, batch_id: str, error: str) -> None:
        """Mark extraction as failed."""
        with self._progress_lock:
            if batch_id not in self._progress_trackers:
                logger.warning("Batch %s not found for failure update", batch_id)
                return

            tracker = self._progress_trackers[batch_id]
        # We intentionally don't hold the lock while logging to avoid potential deadlocks
        tracker["status"] = "failed"
        tracker["error"] = error
        tracker["last_update"] = time.time() * 1000

        logger.error("Extraction failed for batch %s: %s", batch_id, error)

    def update_total_pages(self, batch_id: str, total_pages: int) -> None:
        """Update total page count for a batch."""
        with self._progress_lock:
            if batch_id not in self._progress_trackers:
                return
            self._progress_trackers[batch_id]["total_pages"] = total_pages

    def update_current_operation(
        self,
        batch_id: str,
        document_id: str,
        current_stage: str,
        current_operation: str,
    ) -> None:
        """Update the current operation details."""
        with self._progress_lock:
            if batch_id not in self._progress_trackers:
                return

            tracker = self._progress_trackers[batch_id]
            tracker["current_document"] = document_id
            tracker["current_stage"] = current_stage
            tracker["current_operation"] = current_operation
            tracker["current_operation_started_at"] = datetime.now().isoformat()
            tracker["last_update"] = datetime.now()

    def update_page_progress(
        self,
        batch_id: str,
        pages_processed_count: int,
        current_document: Optional[str] = None,
    ) -> None:
        """Update per-page progress for the current document."""
        with self._progress_lock:
            if batch_id not in self._progress_trackers:
                return

            tracker = self._progress_trackers[batch_id]
            tracker["processed_pages"] = pages_processed_count
            tracker["current_document"] = current_document or tracker["current_document"]
            tracker["last_update"] = datetime.now()

    def get_tracker(self, batch_id: str) -> Optional[Dict[str, Any]]:
        """Expose raw tracker (used for debugging)."""
        with self._progress_lock:
            return self._progress_trackers.get(batch_id)


progress_tracker = ProgressTracker()


def get_progress_tracker() -> ProgressTracker:
    """Return the global text extraction progress tracker instance."""
    return progress_tracker

