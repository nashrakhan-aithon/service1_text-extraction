"""
Training Page Embedder
======================
Generates page-level embeddings using EXACT training pipeline logic.

This ensures page embeddings use the SAME chunking strategy as training:
- Sentence-based chunking (respects semantic boundaries)
- 510-token chunks
- No mid-sentence breaks
- Complete consistency with training data generation
"""

from aithon_imports import setup_imports

setup_imports()

# Import from central embedding service (new location)
from backend.services.embedding import FinBERTVectorizer
import numpy as np
from typing import Tuple, Dict, Any
import logging

logger = logging.getLogger(__name__)


class TrainingPageEmbedder:
    """
    Page embedding using training pipeline for consistency.
    
    This class uses the EXACT same DocumentVectorizer from training,
    ensuring embeddings generated during page classification match
    the training distribution perfectly.
    """

    def __init__(self):
        """
        Initialize with EXACT training parameters.
        
        Parameters match those used in:
        machine_learning/appdoc_classifier_v2_hari/generate_embeddings_service.py
        """
        logger.info("Initializing training page embedder for inference...")

        # Initialize with same parameters as training
        # CRITICAL: chunk_size MUST be 510 (not 512) to match training
        self.vectorizer = FinBERTVectorizer(
            model_name="ProsusAI/finbert",
            chunk_size=510  # CRITICAL: Must match training!
        )

        logger.info("Training page embedder initialized for inference")
        logger.info(f"Model: ProsusAI/finbert, Chunk size: 510 tokens")
        logger.info(f"Device: {self.vectorizer.device}")

    def create_page_embedding(self, page_text: str) -> Tuple[np.ndarray, Dict[str, Any]]:
        """
        Create page embedding using training pipeline's chunking logic.
        
        This ensures page embeddings use the SAME chunking strategy as training:
        - Sentence-based chunking (line 75 in createvector.py)
        - Respects semantic boundaries
        - No mid-sentence breaks
        - 510-token chunks
        
        Args:
            page_text: Single page text (no page markers needed)
        
        Returns:
            Tuple of (embedding, metadata)
            - embedding: 768-dimensional numpy array
            - metadata: Dictionary with keys:
                - chunks: Number of chunks created
                - total_tokens: Total tokens processed
                - avg_tokens_per_chunk: Average tokens per chunk
                - method: Chunking method used
        
        Example:
            >>> embedder = TrainingPageEmbedder()
            >>> text = "The company reported earnings. Revenue increased."
            >>> embedding, metadata = embedder.create_page_embedding(text)
            >>> print(f"Chunks: {metadata['chunks']}, Method: {metadata['method']}")
        """
        if not page_text or not page_text.strip():
            logger.warning("Empty page text provided for embedding")
            return np.zeros(768), {
                "chunks": 0,
                "total_tokens": 0,
                "avg_tokens_per_chunk": 0,
                "method": "empty"
            }

        try:
            # Use training pipeline's sentence-based chunking
            # This is the KEY fix: uses re.split(r"[.!?]+", ...) from training
            page_chunks = self.vectorizer.chunk_text(page_text)

            if not page_chunks:
                logger.warning("No chunks created from page text")
                return np.zeros(768), {
                    "chunks": 0,
                    "total_tokens": 0,
                    "avg_tokens_per_chunk": 0,
                    "method": "failed"
                }

            # Get embeddings for each chunk using training pipeline
            chunk_embeddings = []
            total_tokens = 0

            for chunk in page_chunks:
                # Use training pipeline's get_embedding method
                embedding = self.vectorizer.get_embedding(chunk)
                chunk_embeddings.append(embedding)
                
                # Count tokens for metadata
                tokens = len(self.vectorizer.tokenizer.encode(chunk, add_special_tokens=True))
                total_tokens += tokens

            # Average chunk embeddings (same as training)
            if len(chunk_embeddings) == 1:
                page_embedding = chunk_embeddings[0]
            else:
                page_embedding = np.mean(chunk_embeddings, axis=0)
                logger.debug(f"Averaged {len(chunk_embeddings)} chunk embeddings")

            metadata = {
                "chunks": len(page_chunks),
                "total_tokens": total_tokens,
                "avg_tokens_per_chunk": total_tokens / len(page_chunks) if page_chunks else 0,
                "method": "training_pipeline_sentence_based_chunked" if len(page_chunks) > 1 else "training_pipeline_single"
            }

            return page_embedding, metadata

        except Exception as e:
            logger.error(f"Error creating page embedding: {str(e)}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            # Return zero vector as fallback
            return np.zeros(768), {
                "chunks": 0,
                "total_tokens": 0,
                "avg_tokens_per_chunk": 0,
                "method": "error",
                "error": str(e)
            }

    def is_available(self) -> bool:
        """
        Check if embedder is available and ready to use.
        
        Returns:
            True if vectorizer is initialized and model is loaded, False otherwise
        """
        return self.vectorizer is not None and hasattr(self.vectorizer, "model")


# Singleton instance for reuse across requests
_global_page_embedder = None


def get_training_page_embedder() -> TrainingPageEmbedder:
    """
    Get or create global training page embedder instance.
    
    This ensures we only load the model once and reuse it across requests,
    improving performance and reducing memory usage.
    
    Returns:
        TrainingPageEmbedder instance
    """
    global _global_page_embedder

    if _global_page_embedder is None:
        logger.info("Creating global training page embedder instance...")
        _global_page_embedder = TrainingPageEmbedder()

    return _global_page_embedder

