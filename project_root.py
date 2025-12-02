"""
Robust Project Root Detection
============================

This module provides a reliable way to find the project root directory
regardless of where the script is located in the project structure.

Usage:
    from project_root import get_project_root
    project_root = get_project_root()
    sys.path.insert(0, str(project_root))
"""

import os
import sys
from pathlib import Path

def get_project_root():
    """
    Find the project root directory by looking for marker files.
    
    Returns:
        Path: The absolute path to the project root directory
        
    Raises:
        RuntimeError: If project root cannot be determined
    """
    # Start from the current file's directory
    current_dir = Path(__file__).parent
    
    # Look for project root markers (in order of preference)
    markers = [
        '.envvar',           # Our main config file
        'setup-n-import.sh', # Main setup script
        'start_api_server.py', # Main API server
        'backend/',          # Backend directory
        'frontend/',          # Frontend directory
        'database/',          # Database directory
    ]
    
    # Walk up the directory tree looking for markers
    for path in [current_dir] + list(current_dir.parents):
        for marker in markers:
            if (path / marker).exists():
                return path.resolve()
    
    # If no markers found, try to find by looking for common project files
    for path in [current_dir] + list(current_dir.parents):
        if (path / 'pyproject.toml').exists() or (path / 'requirements.txt').exists():
            return path.resolve()
    
    # Last resort: look for a directory that contains both 'backend' and 'frontend'
    for path in [current_dir] + list(current_dir.parents):
        if (path / 'backend').is_dir() and (path / 'frontend').is_dir():
            return path.resolve()
    
    raise RuntimeError(
        f"Could not determine project root. Searched from: {current_dir}"
    )

def setup_project_imports():
    """
    Set up project imports by adding project root to Python path.
    
    This should be called at the beginning of any script that needs
    to import from the project.
    """
    project_root = get_project_root()
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))
    return project_root

# Convenience function for backward compatibility
def get_project_root_path():
    """Alias for get_project_root() for backward compatibility."""
    return get_project_root()
