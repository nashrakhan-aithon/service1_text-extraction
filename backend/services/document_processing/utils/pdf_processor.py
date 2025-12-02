"""
PDF Processing Utilities - Legacy Redirect
=========================================

⚠️  DEPRECATED: This file has been refactored into smaller, focused modules.

## New Structure

The original large file has been split into focused modules:

- **core_pdf_processor.py**: Core PDF processing engine (PDFProcessor class)
- **ml_text_extractor.py**: ML compatibility wrapper (TextExtractor class)  
- **ml_document_processor.py**: ML training workflows (DocumentProcessor class)

## Backward Compatibility

All existing imports continue to work through this legacy file, but consider
migrating to the new modular structure for better maintainability.

## Recommended Migration

### For Core PDF Processing
```python
# Old (still works)
from backend.services.document_processing.utils.pdf_processor import PDFProcessor

# New (recommended)
from backend.services.document_processing.utils.core_pdf_processor import PDFProcessor
```

### For ML Compatibility
```python
# Old (still works)
from backend.services.document_processing.utils.pdf_processor import TextExtractor

# New (recommended)
from backend.services.document_processing.utils.ml_text_extractor import TextExtractor
```

### For ML Training Workflows
```python
# Old (still works)
from backend.services.document_processing.utils.pdf_processor import DocumentProcessor

# New (recommended)
from backend.services.document_processing.utils.ml_document_processor import DocumentProcessor
```

## Benefits of New Structure

1. **Maintainability**: Smaller, focused modules are easier to maintain
2. **Clarity**: Each module has a single responsibility
3. **Reusability**: Core functionality can be imported independently
4. **Testing**: Easier to write focused unit tests
5. **Performance**: Reduced import overhead for specific use cases

This legacy file will be removed in a future version. Please migrate to the new structure.
"""

# Legacy redirect - import all classes from the new modular structure
from .core_pdf_processor import PDFProcessor
from .ml_text_extractor import TextExtractor
from .ml_document_processor import DocumentProcessor

# Export all classes for backward compatibility
__all__ = [
    'PDFProcessor',
    'TextExtractor', 
    'DocumentProcessor'
]