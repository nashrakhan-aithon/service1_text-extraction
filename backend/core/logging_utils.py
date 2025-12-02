"""
Centralized logging utilities for consistent IST timestamp formatting across all application logs.

This module provides standardized logging functions that ensure all log entries
are timestamped in Indian Standard Time (IST) for consistency and easy debugging.
"""

from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
import logging

# IST timezone offset: UTC+5:30
from zoneinfo import ZoneInfo
IST_TIMEZONE = ZoneInfo("Asia/Kolkata")

def get_ist_timestamp() -> str:
    """
    Get current timestamp formatted for IST (Indian Standard Time).
    
    Returns:
        str: Timestamp in format "YYYY-MM-DD HH:MM:SS IST"
    """
    now_utc = datetime.now(timezone.utc)
    now_ist = now_utc.astimezone(IST_TIMEZONE)
    return now_ist.strftime("%Y-%m-%d %H:%M:%S IST")

def get_ist_timestamp_iso() -> str:
    """
    Get current timestamp in ISO format with IST timezone.
    
    Returns:
        str: Timestamp in format "YYYY-MM-DDTHH:MM:SS+05:30"
    """
    now_utc = datetime.now(timezone.utc)
    now_ist = now_utc.astimezone(IST_TIMEZONE)
    return now_ist.isoformat()

def get_ist_timestamp_compact() -> str:
    """
    Get current timestamp in compact format for log files.
    
    Returns:
        str: Timestamp in format "[YYYY-MM-DD HH:MM:SS IST]"
    """
    return f"[{get_ist_timestamp()}]"

def log_to_file(
    log_file_path: Path, 
    message: str, 
    include_timestamp: bool = True,
    log_level: str = "INFO"
) -> None:
    """
    Write a message to a log file with IST timestamp.
    
    Args:
        log_file_path: Path to the log file
        message: Message to log
        include_timestamp: Whether to include IST timestamp (default: True)
        log_level: Log level (INFO, ERROR, DEBUG, WARNING)
    """
    try:
        # Ensure log directory exists
        log_file_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Format the log entry
        if include_timestamp:
            timestamp = get_ist_timestamp_compact()
            log_entry = f"{timestamp} [{log_level}] {message}\n"
        else:
            log_entry = f"{message}\n"
        
        # Write to file
        with open(log_file_path, "a", encoding="utf-8") as f:
            f.write(log_entry)
            
    except Exception as e:
        # Fallback to standard logger if file writing fails
        logger = logging.getLogger(__name__)
        logger.error(f"Failed to write to log file {log_file_path}: {e}")

def log_error_to_file(
    log_file_path: Path, 
    error_message: str, 
    context: Optional[dict] = None
) -> None:
    """
    Log an error message with context to a file with IST timestamp.
    
    Args:
        log_file_path: Path to the log file
        error_message: Error message to log
        context: Optional context dictionary with additional details
    """
    try:
        # Ensure log directory exists
        log_file_path.parent.mkdir(parents=True, exist_ok=True)
        
        timestamp = get_ist_timestamp_compact()
        
        # Format error log entry
        log_entry = f"{timestamp} [ERROR] {error_message}\n"
        
        # Add context if provided
        if context:
            for key, value in context.items():
                log_entry += f"  {key}: {value}\n"
        
        log_entry += "\n"  # Add blank line for readability
        
        # Write to file
        with open(log_file_path, "a", encoding="utf-8") as f:
            f.write(log_entry)
            
    except Exception as e:
        # Fallback to standard logger if file writing fails
        logger = logging.getLogger(__name__)
        logger.error(f"Failed to write error to log file {log_file_path}: {e}")

def log_debug_to_file(
    log_file_path: Path, 
    debug_message: str, 
    context: Optional[dict] = None
) -> None:
    """
    Log a debug message with context to a file with IST timestamp.
    
    Args:
        log_file_path: Path to the log file
        debug_message: Debug message to log
        context: Optional context dictionary with additional details
    """
    try:
        # Ensure log directory exists
        log_file_path.parent.mkdir(parents=True, exist_ok=True)
        
        timestamp = get_ist_timestamp_compact()
        
        # Format debug log entry
        log_entry = f"{timestamp} [DEBUG] {debug_message}\n"
        
        # Add context if provided
        if context:
            for key, value in context.items():
                log_entry += f"  {key}: {value}\n"
        
        log_entry += "\n"  # Add blank line for readability
        
        # Write to file
        with open(log_file_path, "a", encoding="utf-8") as f:
            f.write(log_entry)
            
    except Exception as e:
        # Fallback to standard logger if file writing fails
        logger = logging.getLogger(__name__)
        logger.error(f"Failed to write debug to log file {log_file_path}: {e}")

def log_validation_errors_to_file(
    log_file_path: Path,
    doc_id: str,
    page_num: int,
    schema_id: str,
    errors: list
) -> None:
    """
    Log validation errors to a file with IST timestamp and structured format.
    
    Args:
        log_file_path: Path to the log file
        doc_id: Document ID
        page_num: Page number
        schema_id: Schema ID
        errors: List of error objects with error_message, row_number, field_name
    """
    try:
        # Ensure log directory exists
        log_file_path.parent.mkdir(parents=True, exist_ok=True)
        
        timestamp = get_ist_timestamp_compact()
        
        # Format validation error log entry
        log_entry = f"{timestamp} [VALIDATION_ERROR] doc_id={doc_id}, page={page_num}, schema={schema_id}\n"
        
        for error in errors:
            log_entry += f"  Error: {error.error_message}\n"
            if hasattr(error, 'row_number') and error.row_number:
                log_entry += f"    Row: {error.row_number}, Field: {error.field_name}\n"
        
        log_entry += "\n"  # Add blank line for readability
        
        # Write to file
        with open(log_file_path, "a", encoding="utf-8") as f:
            f.write(log_entry)
            
    except Exception as e:
        # Fallback to standard logger if file writing fails
        logger = logging.getLogger(__name__)
        logger.error(f"Failed to write validation errors to log file {log_file_path}: {e}")

# Convenience function for backward compatibility
def get_current_ist_time() -> str:
    """Get current IST time - alias for get_ist_timestamp() for backward compatibility."""
    return get_ist_timestamp()
