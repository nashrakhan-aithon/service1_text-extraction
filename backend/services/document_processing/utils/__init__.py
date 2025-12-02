"""
Document Processing Utilities - Unified Imports
==============================================

This module provides unified imports for the refactored document processing utilities.
It maintains backward compatibility while providing access to the new modular structure.

## Refactored Structure

The original large `pdf_processor.py` file has been split into focused modules:

- **core_pdf_processor.py**: Core PDF processing engine (PDFProcessor class)
- **ml_text_extractor.py**: ML compatibility wrapper (TextExtractor class)  
- **ml_document_processor.py**: ML training workflows (DocumentProcessor class)

## Backward Compatibility

All existing imports continue to work:

```python
# These imports still work exactly as before
from backend.services.document_processing.utils.pdf_processor import PDFProcessor
from backend.services.document_processing.utils.pdf_processor import TextExtractor
from backend.services.document_processing.utils.pdf_processor import DocumentProcessor
```

## New Modular Imports

You can also import directly from the new modules:

```python
# Direct imports from specific modules
from backend.services.document_processing.utils.core_pdf_processor import PDFProcessor
from backend.services.document_processing.utils.ml_text_extractor import TextExtractor
from backend.services.document_processing.utils.ml_document_processor import DocumentProcessor
```

## Benefits of Refactoring

1. **Maintainability**: Smaller, focused modules are easier to maintain
2. **Clarity**: Each module has a single responsibility
3. **Reusability**: Core functionality can be imported independently
4. **Testing**: Easier to write focused unit tests
5. **Performance**: Reduced import overhead for specific use cases

## Migration Guide

### For New Code
Use the new modular imports for better clarity:

```python
# For core PDF processing
from backend.services.document_processing.utils.core_pdf_processor import PDFProcessor

# For ML compatibility
from backend.services.document_processing.utils.ml_text_extractor import TextExtractor

# For ML training workflows
from backend.services.document_processing.utils.ml_document_processor import DocumentProcessor
```

### For Existing Code
No changes needed - all existing imports continue to work through the legacy `pdf_processor.py` file.
"""

# Import all classes from the new modular structure
from .core_pdf_processor import PDFProcessor
from .ml_text_extractor import TextExtractor
from .ml_document_processor import DocumentProcessor

# Export all classes for unified access
__all__ = [
    'PDFProcessor',
    'TextExtractor', 
    'DocumentProcessor'
]
