"""
File Management Service for Document Processing
=============================================

Service for handling PDF file operations including download, access, and password management.
Implements CSV password persistence and smart password handling with 3 attempts.
"""

from aithon_imports import setup_imports

setup_imports()

import logging
import os
import shutil
import csv
import aiohttp
from pathlib import Path
from typing import Dict, Any, Optional, List
from backend.core.config import ConfigManager

logger = logging.getLogger(__name__)


class FileManagementService:
    """Service for PDF file operations and password management."""
    
    def __init__(self, default_password: Optional[str] = None):
        """
        Initialize file management service.
        
        Args:
            default_password: Default password for PDF files (from G_DEFAULT_PDF_PWD)
        """
        self.config = ConfigManager(app_type="common")
        # Check environment variables first, then config file
        self.default_password = default_password or os.getenv(
            "G_DEFAULT_PDF_PWD",
            self.config.get_var(
                "G_DEFAULT_PDF_PWD", 
                section="COMMON", 
                fallback="operations@PRI"
            )
        )
        self.password_cache = {}  # filename -> password mapping
        
        # Get datalake path - check environment variables first
        datalake_path = os.getenv(
            "G_AITHON_DATALAKE",
            self.config.get_var(
                "G_AITHON_DATALAKE",
                section="COMMON",
                fallback="~/projects/aithon/aithon_data/datalake-fcr001",
            )
        )
        self.datalake_path = Path(datalake_path).expanduser()
        
        logger.info(f"FileManagementService initialized with default password: {self.default_password}")
        logger.info(f"FileManagementService datalake path: {self.datalake_path}")
    
    async def get_pdf_file(self, doc_info: Dict[str, Any]) -> Optional[str]:
        """Get PDF file path, downloading if necessary."""
        doc_id = doc_info["doc_id"]
        
        # Check if file already exists in datalake
        doc_folder = self.datalake_path / doc_id
        pdf_path = doc_folder / "source.pdf"
        
        if pdf_path.exists():
            logger.info(f"PDF file already exists: {pdf_path}")
            return str(pdf_path)
        
        # Create document folder
        doc_folder.mkdir(parents=True, exist_ok=True)
        
        # Check if we have a local file path first, then source URI
        datalake_uri = doc_info.get("datalake_raw_uri")
        source_uri = doc_info.get("source_uri")
        
        # First check if we have a local file path
        if datalake_uri and os.path.exists(datalake_uri):
            shutil.copy2(datalake_uri, pdf_path)
            logger.info(f"Copied PDF file to datalake: {pdf_path}")
            return str(pdf_path)
        
        # Then check source URI for download
        if source_uri:
            if os.path.exists(source_uri):
                shutil.copy2(source_uri, pdf_path)
                logger.info(f"Copied PDF file to datalake: {pdf_path}")
                return str(pdf_path)
            elif source_uri.startswith(("http://", "https://")):
                try:
                    await self.download_pdf_from_url(source_uri, pdf_path)
                    logger.info(f"Downloaded PDF file to datalake: {pdf_path}")
                    return str(pdf_path)
                except Exception as e:
                    logger.error(f"Failed to download PDF from {source_uri}: {str(e)}")
                    return None
        
        logger.error(f"No source PDF file found for document {doc_id}")
        return None
    
    async def download_pdf_from_url(self, url: str, output_path: Path) -> None:
        """Download PDF from URL."""
        # Convert GitHub blob URL to raw URL
        if "github.com" in url and "/blob/" in url:
            url = url.replace("/blob/", "/raw/")
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200:
                    with open(output_path, "wb") as f:
                        async for chunk in response.content.iter_chunked(8192):
                            f.write(chunk)
                else:
                    raise Exception(f"HTTP {response.status}: Failed to download PDF")
    
    def get_password_for_file(self, pdf_path: str, provided_password: Optional[str] = None) -> Optional[str]:
        """Get password for a PDF file using multiple strategies."""
        filename = Path(pdf_path).name
        
        # 1. Use provided password
        if provided_password:
            return provided_password
        
        # 2. Use cached password
        if filename in self.password_cache:
            return self.password_cache[filename]
        
        # 3. Use default password
        return self.default_password
    
    def cache_successful_password(self, pdf_path: str, password: str):
        """Cache a successful password for future use."""
        filename = Path(pdf_path).name
        self.password_cache[filename] = password
        logger.info(f"Cached password for {filename}")
    
    def get_password_csv_path(self, pdf_path: str) -> Path:
        """Get the path to the password CSV file for a PDF."""
        pdf_dir = Path(pdf_path).parent
        return pdf_dir / "file_passwords.csv"
    
    def load_saved_passwords(self, pdf_path: str) -> Dict[str, str]:
        """Load saved passwords from CSV file for a PDF directory."""
        password_file = self.get_password_csv_path(pdf_path)
        passwords = {}
        
        if password_file.exists():
            try:
                with password_file.open("r", encoding="utf-8") as f:
                    reader = csv.reader(f)
                    # Skip header if present
                    first_row = next(reader, None)
                    if first_row and first_row != ["pdf_filename", "password"]:
                        passwords[first_row[0]] = first_row[1]
                    
                    for row in reader:
                        if len(row) >= 2:
                            passwords[row[0]] = row[1]
            except Exception as e:
                logger.warning(f"Error loading passwords from {password_file}: {e}")
        
        return passwords
    
    def save_password_to_csv(self, pdf_path: str, password: str):
        """Save a successful password to CSV file."""
        password_file = self.get_password_csv_path(pdf_path)
        passwords = self.load_saved_passwords(pdf_path)
        
        filename = Path(pdf_path).name
        passwords[filename] = password
        
        # Ensure output directory exists
        password_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Write all passwords to CSV
        with password_file.open("w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["pdf_filename", "password"])
            for filename, pwd in sorted(passwords.items()):
                writer.writerow([filename, pwd])
        
        logger.info(f"Saved password for {filename} to {password_file}")
    
    def get_all_passwords_for_file(self, pdf_path: str, provided_password: Optional[str] = None) -> List[str]:
        """Get all possible passwords for a PDF file (for 3 attempts)."""
        filename = Path(pdf_path).name
        passwords = []
        
        # 1. Provided password
        if provided_password:
            passwords.append(provided_password)
        
        # 2. Load saved passwords from CSV
        saved_passwords = self.load_saved_passwords(pdf_path)
        if filename in saved_passwords and saved_passwords[filename] not in passwords:
            passwords.append(saved_passwords[filename])
        
        # 3. Cached password
        if filename in self.password_cache and self.password_cache[filename] not in passwords:
            passwords.append(self.password_cache[filename])
        
        # 4. Default password
        if self.default_password and self.default_password not in passwords:
            passwords.append(self.default_password)
        
        # 5. Try without password (None)
        passwords.append(None)
        
        return passwords
    
    def save_successful_password(self, pdf_path: str, password: str):
        """Save a successful password to both cache and CSV."""
        self.cache_successful_password(pdf_path, password)
        self.save_password_to_csv(pdf_path, password)
    
    def get_service_stats(self) -> Dict[str, Any]:
        """Get file management service statistics."""
        return {
            "default_password": self.default_password,
            "cached_passwords_count": len(self.password_cache),
            "datalake_path": str(self.datalake_path),
            "password_cache": dict(self.password_cache)
        }
