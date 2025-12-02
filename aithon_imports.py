"""
Aithon Framework v2 - Production Import Manager
==============================================

Solution 1: Production-Ready Import Path Management
This is the DEFINITIVE solution for import path issues.

Usage in ANY Python file:
    from aithon_imports import setup_imports
    setup_imports()

    # Now ALL imports work consistently:
    from backend.services.master_data import master_data_router
    from backend.core import AIUtils
    from shared.dark_theme import apply_dark_theme

This approach:
✅ Works in production, development, and testing
✅ No package installation required
✅ Consistent across all environments
✅ Simple to use - just one import and call
✅ Auto-detects project root intelligently
"""

import sys
import os
from pathlib import Path
from typing import Optional, List


def find_project_root(start_path: Optional[Path] = None) -> Path:
    """
    Intelligently find the project root directory.

    Looks for these markers (in order of preference):
    1. pyproject.toml (Python package standard)
    2. setup.py (Traditional Python package)
    3. backend/ and backend/core/ directories (Aithon-specific)
    4. .git/ directory (Git repository root)

    Args:
        start_path: Starting path to search from (defaults to current file location)

    Returns:
        Path to project root directory

    Raises:
        RuntimeError: If project root cannot be found
    """
    if start_path is None:
        start_path = Path(__file__).parent.absolute()

    current_path = start_path

    # Search up the directory tree
    while current_path != current_path.parent:
        # Check for Python package markers
        if (current_path / "pyproject.toml").exists():
            return current_path
        if (current_path / "setup.py").exists():
            return current_path

        # Check for Aithon-specific markers
        if (current_path / "backend").exists() and (
            current_path / "backend/core"
        ).exists():
            return current_path

        # Check for Git repository
        if (current_path / ".git").exists():
            return current_path

        current_path = current_path.parent

    # Fallback: return the starting directory if nothing found
    print(f"⚠️  Warning: Could not find project root markers, using {start_path}")
    return start_path


def setup_imports(verbose: bool = False) -> Path:
    """
    Setup import paths for consistent module imports across the entire project.

    This function:
    1. Finds the project root intelligently
    2. Adds necessary paths to sys.path
    3. Sets environment variables
    4. Returns the project root path

    Args:
        verbose: Print detailed information about path setup

    Returns:
        Path to the project root directory
    """
    # Find project root
    project_root = find_project_root()

    # Paths to add to sys.path (in order of priority)
    paths_to_add = [
        project_root,  # For: from backend.services import ...
        project_root / "backend/core",  # For: from backend.core import ...
        project_root / "shared" / "utils",  # For: from dark_theme import ...
        project_root / "ai_services",  # For: from models import ...
    ]

    # Add paths to sys.path (avoid duplicates)
    added_paths = []
    for path in paths_to_add:
        path_str = str(path)
        if path.exists() and path_str not in sys.path:
            sys.path.insert(0, path_str)
            added_paths.append(path_str)

    # Set environment variables
    os.environ.setdefault("AITHON_PROJECT_ROOT", str(project_root))
    if "PYTHONPATH" in os.environ:
        os.environ["PYTHONPATH"] = f"{project_root}:{os.environ['PYTHONPATH']}"
    else:
        os.environ["PYTHONPATH"] = str(project_root)

    if verbose:
        print(f"🏠 Project Root: {project_root}")
        print(f"📁 Added {len(added_paths)} paths to sys.path:")
        for path in added_paths:
            print(f"   ✅ {path}")
        print(f"🌍 PYTHONPATH: {os.environ.get('PYTHONPATH', 'Not set')}")

    return project_root


# Convenience function for testing imports
def test_imports() -> bool:
    """
    Test that key imports work after setup.

    Returns:
        True if all imports successful, False otherwise
    """
    test_imports_list = [
        ("backend.services.master_data", "master_data_router"),
        ("backend/core", "AIUtils"),
    ]

    success = True
    print("🧪 Testing imports...")

    for module_name, attr_name in test_imports_list:
        try:
            module = __import__(module_name, fromlist=[attr_name])
            getattr(module, attr_name)
            print(f"   ✅ {module_name}.{attr_name}")
        except Exception as e:
            print(f"   ❌ {module_name}.{attr_name} - {e}")
            success = False

    return success


def get_project_info() -> dict:
    """Get information about the current project setup."""
    project_root = find_project_root()

    info = {
        "project_root": str(project_root),
        "python_paths": sys.path[:5],  # First 5 paths
        "environment": {
            "AITHON_PROJECT_ROOT": os.environ.get("AITHON_PROJECT_ROOT"),
            "PYTHONPATH": os.environ.get("PYTHONPATH"),
        },
        "markers_found": {
            "pyproject.toml": (project_root / "pyproject.toml").exists(),
            "setup.py": (project_root / "setup.py").exists(),
            "backend/": (project_root / "backend").exists(),
            "backend/core/": (project_root / "backend/core").exists(),
            ".git/": (project_root / ".git").exists(),
        },
    }

    return info


# Auto-setup when imported (optional - can be disabled)
_AUTO_SETUP = os.environ.get("AITHON_AUTO_IMPORTS", "true").lower() == "true"

if _AUTO_SETUP:
    try:
        setup_imports()
    except Exception as e:
        print(f"⚠️  Auto-import setup failed: {e}")


# Export key functions
__all__ = ["setup_imports", "test_imports", "get_project_info", "find_project_root"]


if __name__ == "__main__":
    # When run directly, show detailed setup information
    print("🚀 Aithon Framework v2 - Import Setup")
    print("=" * 50)

    # Setup imports with verbose output
    project_root = setup_imports(verbose=True)

    print()
    print("📊 Project Information:")
    info = get_project_info()
    for category, data in info.items():
        if isinstance(data, dict):
            print(f"   {category}:")
            for key, value in data.items():
                print(f"      {key}: {value}")
        else:
            print(f"   {category}: {data}")

    print()
    # Test imports
    success = test_imports()

    print()
    if success:
        print("🎉 SUCCESS: All import paths configured correctly!")
        print("📋 Copy this line to any Python file:")
        print("   from aithon_imports import setup_imports; setup_imports()")
    else:
        print("❌ FAILED: Some imports are not working. Check your project structure.")

    print("\n🔧 Production Usage:")
    print("   Add this to any Python file that needs imports:")
    print("   ```python")
    print("   from aithon_imports import setup_imports")
    print("   setup_imports()")
    print("   ```")
