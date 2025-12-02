"""
Training Vectorizer Wrapper
============================

Wrapper for training pipeline's DocumentVectorizer to ensure prediction embeddings
match training embeddings exactly.

This wrapper uses the EXACT same DocumentVectorizer that was used during model training,
ensuring that embeddings generated during prediction have the same characteristics:
- Same model (ProsusAI/finbert)
- Same chunk size (510 tokens)
- Same text cleaning logic
- Same page splitting logic
- Same averaging strategy
"""

from aithon_imports import setup_imports

setup_imports()

# Import from central embedding service (new location)
from backend.services.embedding import FinBERTVectorizer
import numpy as np
from typing import Tuple, Dict, Any
import logging

logger = logging.getLogger(__name__)


class TrainingVectorizerWrapper:
    """
    Wrapper for training pipeline's DocumentVectorizer for use in prediction.
    
    This class ensures that embeddings generated during prediction use the exact
    same pipeline as training, guaranteeing consistency between training and inference.
    """

    def __init__(self):
        """
        Initialize with EXACT training parameters.
        
        Parameters must match those used in:
        machine_learning/appdoc_classifier_v2_hari/generate_embeddings_service.py
        """
        logger.info("Initializing training vectorizer for prediction...")
        
        # Initialize with same parameters as training
        # CRITICAL: chunk_size MUST be 510 (not 512) to match training
        self.vectorizer = FinBERTVectorizer(
            model_name="ProsusAI/finbert",
            chunk_size=510  # CRITICAL: Must match training (not 512!)
        )
        
        logger.info("Training vectorizer initialized for prediction")
        logger.info(f"Model: ProsusAI/finbert, Chunk size: 510 tokens")
        logger.info(f"Device: {self.vectorizer.device}")

    def create_document_embedding(
        self, text: str
    ) -> Tuple[np.ndarray, Dict[str, Any]]:
        """
        Create document embedding using training pipeline.
        
        This method uses the exact same logic as the training pipeline:
        1. Text cleaning (done internally by DocumentVectorizer)
        2. Page splitting using --- PAGE X --- markers
        3. Chunking into 510-token chunks
        4. Embedding generation with FinBERT
        5. Chunk averaging within pages
        6. Page averaging for document embedding
        
        Args:
            text: Document text WITH page markers (--- PAGE X ---)
                  Text should be in the format produced by extract_text_from_pdf_simple():
                  "--- PAGE 1 ---\nPage 1 text\n--- PAGE 2 ---\nPage 2 text\n..."
            
        Returns:
            Tuple of (embedding, metadata)
            - embedding: 768-dimensional numpy array
            - metadata: Dictionary with keys:
                - pages: Number of pages processed
                - chunks: Total number of chunks processed
                - total_tokens: Total number of tokens processed
                - avg_tokens_per_chunk: Average tokens per chunk
        
        Example:
            >>> wrapper = TrainingVectorizerWrapper()
            >>> text = "--- PAGE 1 ---\\nSome text here\\n--- PAGE 2 ---\\nMore text\\n"
            >>> embedding, metadata = wrapper.create_document_embedding(text)
            >>> print(f"Embedding shape: {embedding.shape}")
            >>> print(f"Metadata: {metadata}")
        """
        if not text or not text.strip():
            logger.warning("Empty text provided for embedding generation")
            return np.zeros(768), {
                "pages": 0,
                "chunks": 0,
                "total_tokens": 0,
                "avg_tokens_per_chunk": 0,
            }

        try:
            # Use training pipeline's create_document_embedding method
            # This handles all the text cleaning, page splitting, chunking, and averaging
            embedding, metadata = self.vectorizer.create_document_embedding(text)

            logger.info(
                f"Generated embedding: {embedding.shape[0]} dimensions, "
                f"{metadata.get('pages', 0)} pages, {metadata.get('chunks', 0)} chunks"
            )

            return embedding, metadata

        except Exception as e:
            logger.error(f"Error generating embedding: {str(e)}")
            # Return zero vector as fallback
            return np.zeros(768), {
                "pages": 0,
                "chunks": 0,
                "total_tokens": 0,
                "avg_tokens_per_chunk": 0,
                "error": str(e),
            }

    def is_available(self) -> bool:
        """
        Check if the vectorizer is available and ready to use.
        
        Returns:
            True if vectorizer is initialized and model is loaded, False otherwise
        """
        return self.vectorizer is not None and hasattr(self.vectorizer, "model")


# Singleton instance for reuse across requests
_global_training_vectorizer = None


def get_training_vectorizer() -> TrainingVectorizerWrapper:
    """
    Get or create global training vectorizer instance.
    
    This ensures we only load the model once and reuse it across requests,
    improving performance and reducing memory usage.
    
    Returns:
        TrainingVectorizerWrapper instance
    """
    global _global_training_vectorizer

    if _global_training_vectorizer is None:
        logger.info("Creating global training vectorizer instance...")
        _global_training_vectorizer = TrainingVectorizerWrapper()

    return _global_training_vectorizer

