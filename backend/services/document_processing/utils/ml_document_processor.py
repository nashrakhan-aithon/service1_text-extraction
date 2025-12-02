"""
ML Document Processor - Training Workflows
=========================================

This module provides comprehensive ML training workflow capabilities, combining
PDF processing with machine learning data preparation. It handles folder parsing,
embedding creation, and CSV output management for ML training workflows.

Features:
- Handles both individual PDF processing and batch ML training workflows
- Automatic folder parsing for ML training datasets
- Embedding creation and CSV output management
- Progress tracking and resume capabilities
- Integration with document vectorization services
- Incremental processing with skip capabilities
"""

import logging
import os
import json
from pathlib import Path
from typing import Dict, List, Tuple, Any
from datetime import datetime

from .core_pdf_processor import PDFProcessor

logger = logging.getLogger(__name__)


class DocumentProcessor:
    """
    Unified document processor that combines PDF processing and ML training capabilities.
    
    This class provides a comprehensive solution for both individual PDF processing and
    batch ML training workflows. It automatically handles folder parsing, class extraction,
    embedding creation, and CSV output management for machine learning workflows.
    
    Features:
    - Handles both individual PDF processing and batch ML training workflows
    - Automatic folder parsing for ML training datasets
    - Embedding creation and CSV output management
    - Progress tracking and resume capabilities
    - Integration with document vectorization services
    - Incremental processing with skip capabilities
    
    Args:
        data_folder (str, optional): Path to folder containing document subfolders (for ML training)
        output_folder (str, optional): Path to save output files (for ML training)
        max_pages (int): Maximum number of pages to process per document (default: 50)
        min_text_length (int): Minimum text length to consider extraction successful (default: 100)
        verbose (bool): Enable verbose logging for debugging (default: False)
    
    Example:
        >>> # ML Training Mode
        >>> processor = DocumentProcessor(
        ...     data_folder="/path/to/training/data",
        ...     output_folder="/path/to/output",
        ...     max_pages=50
        ... )
        >>> output_path = processor.run_processing()
        >>> print(f"Training data saved to: {output_path}")
        
        >>> # Individual Document Processing
        >>> processor = DocumentProcessor()
        >>> result = processor.process_single_document("document.pdf", "AGM", "Annual-General-meetings")
        >>> if result:
        ...     print(f"Processed: {result['document_name']}, Text length: {result['text_length']}")
    """
    
    def __init__(self, data_folder: str = None, output_folder: str = None, 
                 max_pages: int = 50, min_text_length: int = 100, verbose: bool = False):
        """
        Initialize the unified document processor.
        
        Args:
            data_folder: Path to folder containing document subfolders (for ML training)
            output_folder: Path to save output files (for ML training)
            max_pages: Maximum number of pages to process per document
            min_text_length: Minimum text length to consider extraction successful
            verbose: Enable verbose logging for debugging
        """
        self.data_folder = data_folder
        self.output_folder = output_folder
        
        # Initialize PDF processor
        self.pdf_processor = PDFProcessor(
            max_pages=max_pages,
            min_text_length=min_text_length,
            verbose=verbose
        )
        
        # Initialize ML components if folders provided
        if data_folder and output_folder:
            try:
                # Import from central embedding service
                from backend.services.embedding import FinBERTVectorizer as DocumentVectorizer
                self.vectorizer = DocumentVectorizer()
                os.makedirs(output_folder, exist_ok=True)
                logger.info(f"ML training mode: Data folder: {data_folder}, Output folder: {output_folder}")
            except ImportError:
                logger.warning("DocumentVectorizer not available. ML training features disabled.")
                self.vectorizer = None
        else:
            self.vectorizer = None
            logger.info("PDF processing mode only")
    
    def parse_folder_name(self, folder_name: str) -> Tuple[str, str]:
        """
        Parse folder name to extract class and full class name.
        
        Args:
            folder_name: Folder name like "LF_AGM_Annual-General-meetings"
            
        Returns:
            Tuple of (class, full_class_name)
        """
        try:
            parts = folder_name.split("_")
            if len(parts) >= 3:
                class_name = parts[1]
                full_class_name = parts[2]
                return class_name, full_class_name
            else:
                logger.warning(f"Unexpected folder name format: {folder_name}")
                return folder_name, folder_name
        except Exception as e:
            logger.error(f"Error parsing folder name {folder_name}: {str(e)}")
            return folder_name, folder_name
    
    def get_document_folders(self) -> List[str]:
        """Get all document folders in the data directory."""
        if not self.data_folder:
            raise ValueError("Data folder not specified")
            
        folders = []
        for item in os.listdir(self.data_folder):
            item_path = os.path.join(self.data_folder, item)
            if os.path.isdir(item_path):
                folders.append(item)
        
        logger.info(f"Found {len(folders)} document folders")
        return sorted(folders)
    
    def get_pdf_files(self, folder_path: str) -> List[str]:
        """Get all PDF files in a folder."""
        import glob
        
        pdf_pattern = os.path.join(folder_path, "*.pdf")
        pdf_files = glob.glob(pdf_pattern, recursive=False)
        
        # Also check for PDFs in subfolders
        pdf_pattern_recursive = os.path.join(folder_path, "**", "*.pdf")
        pdf_files.extend(glob.glob(pdf_pattern_recursive, recursive=True))
        
        return list(set(pdf_files))  # Remove duplicates
    
    def process_single_document(self, pdf_path: str, class_name: str = None, 
                               full_class_name: str = None) -> Dict:
        """
        Process a single PDF document with optional ML training features.
        
        Args:
            pdf_path: Path to PDF file
            class_name: Document class (for ML training)
            full_class_name: Full class name (for ML training)
            
        Returns:
            Dictionary with document information and optional embedding
        """
        document_name = os.path.basename(pdf_path)
        
        try:
            # Extract text using PDF processor
            logger.info(f"Extracting text from: {document_name}")
            text, used_ocr = self.pdf_processor.extract_text_from_pdf_simple(pdf_path)
            
            if not text.strip():
                logger.warning(f"No text extracted from {document_name}")
                return None
            
            # Prepare base result
            result = {
                "document_name": document_name,
                "document_path": pdf_path,
                "text_length": len(text),
                "used_ocr": used_ocr,
                "text": text
            }
            
            # Add ML training features if vectorizer available and class info provided
            if self.vectorizer and class_name and full_class_name:
                logger.info(f"Creating embedding for: {document_name}")
                embedding, metadata = self.vectorizer.create_document_embedding(text)
                
                result.update({
                    "class": class_name,
                    "full_class_name": full_class_name,
                    "chunks_processed": metadata["chunks"],
                    "total_tokens": metadata["total_tokens"],
                    "avg_tokens_per_chunk": metadata["avg_tokens_per_chunk"],
                    "embedding": embedding.tolist(),  # Convert numpy array to list for JSON serialization
                })
            
            logger.info(f"Successfully processed {document_name}")
            return result
            
        except Exception as e:
            logger.error(f"Error processing {document_name}: {str(e)}")
            return None
    
    def check_existing_embeddings(self) -> set:
        """Check which documents have already been processed."""
        if not self.output_folder:
            return set()
            
        embeddings_file = os.path.join(self.output_folder, "document_embedding.csv")
        processed_files = set()
        
        if os.path.exists(embeddings_file):
            try:
                import pandas as pd
                existing_df = pd.read_csv(embeddings_file)
                processed_files = set(existing_df["document_path"].tolist())
                logger.info(f"Found {len(processed_files)} already processed documents")
            except Exception as e:
                logger.warning(f"Could not read existing embeddings file: {str(e)}")
        
        return processed_files
    
    def save_single_document_embedding(self, result: Dict):
        """Save a single document's embedding to CSV immediately."""
        if not result or not self.output_folder or "embedding" not in result:
            return
        
        embeddings_file = os.path.join(self.output_folder, "document_embedding.csv")
        
        # Convert result to DataFrame row
        embedding_list = result["embedding"]
        
        # Create row data
        row_data = {
            "document_name": result["document_name"],
            "document_path": result["document_path"],
            "class": result["class"],
            "full_class_name": result["full_class_name"],
            "text_length": result["text_length"],
            "used_ocr": result["used_ocr"],
            "chunks_processed": result["chunks_processed"],
            "total_tokens": result["total_tokens"],
            "avg_tokens_per_chunk": result["avg_tokens_per_chunk"],
        }
        
        # Add embedding columns
        for i, value in enumerate(embedding_list):
            row_data[f"embedding_{i}"] = value
        
        import pandas as pd
        row_df = pd.DataFrame([row_data])
        
        # Append to CSV file
        if os.path.exists(embeddings_file):
            # Append without header
            row_df.to_csv(embeddings_file, mode="a", header=False, index=False)
        else:
            # Create new file with header
            row_df.to_csv(embeddings_file, mode="w", header=True, index=False)
        
        logger.info(f"Saved embedding for: {result['document_name']}")
    
    def process_all_documents(self) -> Any:
        """
        Process all documents in the data folder for ML training.
        
        Returns:
            DataFrame with document embeddings and metadata
        """
        if not self.data_folder or not self.output_folder:
            raise ValueError("Data folder and output folder must be specified for ML training")
        
        folders = self.get_document_folders()
        logger.info(f"Starting processing of {len(folders)} folders")
        
        # Check for already processed documents
        processed_files = self.check_existing_embeddings()
        
        total_processed = 0
        skipped_count = 0
        
        for folder_name in folders:
            folder_path = os.path.join(self.data_folder, folder_name)
            class_name, full_class_name = self.parse_folder_name(folder_name)
            
            logger.info(f"Processing folder: {folder_name} (class: {class_name})")
            
            # Get PDF files in folder
            pdf_files = self.get_pdf_files(folder_path)
            logger.info(f"Found {len(pdf_files)} PDF files in {folder_name}")
            
            if not pdf_files:
                logger.warning(f"No PDF files found in {folder_name}")
                continue
            
            # Process each PDF
            for pdf_path in pdf_files:
                # Skip if already processed
                if pdf_path in processed_files:
                    logger.info(f"Skipping already processed: {os.path.basename(pdf_path)}")
                    skipped_count += 1
                    continue
                
                result = self.process_single_document(pdf_path, class_name, full_class_name)
                
                if result:
                    # Save immediately
                    self.save_single_document_embedding(result)
                    total_processed += 1
                    
                    # Log progress
                    if total_processed % 10 == 0:
                        logger.info(f"Progress: {total_processed} documents processed")
        
        logger.info(f"Processing completed!")
        logger.info(f"New documents processed: {total_processed}")
        logger.info(f"Already processed (skipped): {skipped_count}")
        
        # Load and return the complete dataset
        embeddings_file = os.path.join(self.output_folder, "document_embedding.csv")
        if os.path.exists(embeddings_file):
            import pandas as pd
            final_df = pd.read_csv(embeddings_file)
            logger.info(f"Final dataset contains {len(final_df)} documents")
            return final_df
        else:
            logger.error("No embeddings file found after processing!")
            return pd.DataFrame()
    
    def create_processing_summary(self, df: Any):
        """Create a processing summary file."""
        if not self.output_folder:
            return
            
        # Convert pandas/numpy types to native Python types for JSON serialization
        class_counts = df["class"].value_counts()
        
        summary = {
            "total_documents": int(len(df)),
            "classes": {str(k): int(v) for k, v in class_counts.items()},
            "processing_date": datetime.now().isoformat(),
            "embedding_dimension": len([col for col in df.columns if col.startswith("embedding_")]),
            "class_distribution": {str(k): int(v) for k, v in class_counts.items()},
            "processing_stats": {
                "avg_text_length": float(df["text_length"].mean()),
                "ocr_usage_rate": float(df["used_ocr"].mean()),
                "avg_chunks_per_doc": float(df["chunks_processed"].mean()),
                "total_tokens_processed": int(df["total_tokens"].sum()),
            },
        }
        
        summary_path = os.path.join(self.output_folder, "processing_summary.json")
        with open(summary_path, "w") as f:
            json.dump(summary, f, indent=2)
        
        logger.info(f"Saved processing summary to: {summary_path}")
        
        # Print summary to console
        logger.info("=== PROCESSING SUMMARY ===")
        logger.info(f"Total documents: {summary['total_documents']}")
        logger.info(f"Classes found: {len(summary['classes'])}")
        logger.info("Class distribution:")
        for class_name, count in summary["classes"].items():
            logger.info(f"  {class_name}: {count} documents")
        logger.info(f"Average text length: {summary['processing_stats']['avg_text_length']:.0f} chars")
        logger.info(f"OCR usage rate: {summary['processing_stats']['ocr_usage_rate']:.1%}")
        logger.info("==========================")
    
    def run_processing(self) -> str:
        """
        Run the complete document processing pipeline for ML training.
        
        This method orchestrates the entire ML training workflow:
        1. Scans the data folder for document subfolders
        2. Parses folder names to extract class information
        3. Processes all PDF files in each folder
        4. Creates embeddings for each document
        5. Saves results to CSV files
        6. Generates processing summary
        
        Returns:
            str: Path to the generated embeddings CSV file
            
        Raises:
            ValueError: If data_folder or output_folder not specified
            Exception: If no documents were processed successfully
            
        Example:
            >>> processor = DocumentProcessor(
            ...     data_folder="/path/to/training/data",
            ...     output_folder="/path/to/output"
            ... )
            >>> output_path = processor.run_processing()
            >>> print(f"Training data saved to: {output_path}")
        """
        if not self.data_folder or not self.output_folder:
            raise ValueError("Data folder and output folder must be specified for ML training")
            
        logger.info("Starting document processing pipeline")
        
        try:
            # Process all documents
            df = self.process_all_documents()
            
            if df.empty:
                raise Exception("No documents were processed successfully")
            
            # Create summary
            self.create_processing_summary(df)
            
            # Print summary
            logger.info("Processing completed successfully!")
            logger.info(f"Total documents processed: {len(df)}")
            logger.info(f"Classes found: {df['class'].nunique()}")
            logger.info("Class distribution:")
            for class_name, count in df["class"].value_counts().items():
                logger.info(f"  {class_name}: {count} documents")
            
            embeddings_file = os.path.join(self.output_folder, "document_embedding.csv")
            return embeddings_file
            
        except Exception as e:
            logger.error(f"Processing failed: {str(e)}")
            raise
