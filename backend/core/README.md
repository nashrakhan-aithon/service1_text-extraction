# Aithon Core SDK

## 🎯 Purpose

**Eliminate code duplication across microservices** by providing shared functionality that all Aithon services need.

## 🚨 Problem Solved

**BEFORE Aithon Core SDK:**
```python
# msb-service/service.py
def find_pdf_file(filename):
    for folder in [msb_data, general_data]:  # 🔴 DUPLICATE
        path = Path(folder) / filename
        if path.exists(): return str(path)
    return None

# classification-service/service.py  
def find_pdf_file(filename):
    for folder in [msb_data, general_data]:  # 🔴 SAME CODE!
        path = Path(folder) / filename
        if path.exists(): return str(path)
    return None

# extraction-service/service.py
def find_pdf_file(filename):
    for folder in [msb_data, general_data]:  # 🔴 SAME CODE!
        path = Path(folder) / filename  
        if path.exists(): return str(path)
    return None
```

**AFTER Aithon Core SDK:**
```python
# All services use the same shared code
from backend.core import FileManager, ConfigManager

config = ConfigManager("msb")
file_manager = FileManager(config.get_path_config())
pdf_path = file_manager.find_file_or_raise("document.pdf")  # ✅ SINGLE SOURCE!
```

---

## 🏗️ Architecture

### **Shared Across ALL Services:**
```
backend/core/
├── file_operations.py    # File discovery, path resolution, status checking
├── pdf_processing.py     # PDF loading, text extraction, validation  
├── config.py            # Configuration management
└── types.py             # Common data models
```

### **Benefits:**
- ✅ **Single Source of Truth** - Fix once, works everywhere
- ✅ **Consistent Behavior** - All services work the same way
- ✅ **Easy Testing** - Test core logic once  
- ✅ **Faster Development** - No need to rewrite common functionality

---

## 📖 Quick Start

### **1. Basic File Operations**
```python
from backend.core import ConfigManager, FileManager

# Initialize
config = ConfigManager("msb")  # or "fs", "docc", etc.
file_manager = FileManager(config.get_path_config())

# Find files across all data folders
pdf_path = file_manager.find_file("document.pdf")
if pdf_path:
    print(f"Found PDF at: {pdf_path}")

# Check if page has been processed
already_processed = file_manager.check_file_processed("document.pdf", page_num=0)

# Get output folder for a document
output_folder = file_manager.get_output_folder("document.pdf", "extracted_text")
```

### **2. PDF Processing**
```python
from backend.core import PDFProcessorFactory

# Create PDF processor
processor = PDFProcessorFactory.create_processor("simple")

# Load and process
page_count = processor.load_pdf("/path/to/document.pdf")
text = processor.extract_text(page_num=0)  # 0-indexed
image = processor.get_page_image(page_num=0, zoom=2.0)

# Always clean up
processor.close()

# Or use convenience functions
from backend.core.pdf_processing import quick_extract_text, quick_get_page_count

text = quick_extract_text("/path/to/document.pdf", page_num=0)
pages = quick_get_page_count("/path/to/document.pdf") 
```

### **3. Configuration Management**
```python
from backend.core import ConfigManager

# App-specific configuration
config = ConfigManager("msb")

# Get paths for this app type
paths = config.get_path_config()
print(f"Data folders: {paths.data_folders}")
print(f"Output folder: {paths.output_folder}")

# Get OpenAI configuration
openai_config = config.get_openai_config()

# Load prompts
system_prompt = config.get_prompt("msb_system_prompt")
```

### **4. PDF Discovery**
```python
from backend.core import ConfigManager, FileManager, PDFDiscovery

config = ConfigManager("msb")
file_manager = FileManager(config.get_path_config())
pdf_discovery = PDFDiscovery(file_manager)

# Discover all PDFs in a folder
pdfs = pdf_discovery.discover_pdfs("/data/folder")
for pdf in pdfs:
    print(f"PDF: {pdf.filename}, Status: {pdf.processing_status}")

# Get all processed documents
processed = pdf_discovery.get_processed_documents()
```

---

## 🔧 Service Integration Examples

### **Backend Web API Integration**
```python
# backend/app/services/
from backend.core import AIUtils, JSONProcessor, TextProcessor, BasicPDFUtils

# All backend services now use backend.core utilities
ai_utils = AIUtils(ConfigManager("backend"))
json_processor = JSONProcessor()
text_processor = TextProcessor()
pdf_utils = BasicPDFUtils()
```

### **MSB Service**
```python
from backend.core import ConfigManager, FileManager, PDFDiscovery

class MSBFileService:
    def __init__(self):
        self.config = ConfigManager("msb")
        self.file_manager = FileManager(self.config.get_path_config())  
        self.pdf_discovery = PDFDiscovery(self.file_manager)
    
    def get_pdf_files(self, folder_path: str):
        return self.pdf_discovery.discover_pdfs(folder_path)
    
    def start_extraction(self, document_name: str):
        pdf_path = self.file_manager.find_file_or_raise(document_name)
        # ... extraction logic
```

### **Classification Service**
```python
from backend.core import ConfigManager, FileManager, PDFProcessorFactory

class ClassificationService:
    def __init__(self):
        self.config = ConfigManager("classification")
        self.file_manager = FileManager(self.config.get_path_config())
        
    def classify_document(self, document_name: str):
        pdf_path = self.file_manager.find_file_or_raise(document_name)
        processor = PDFProcessorFactory.create_processor()
        # ... classification logic
```

### **Data Extraction Service**  
```python
from backend.core import ConfigManager, FileManager

class DataExtractionService:
    def __init__(self):
        self.config = ConfigManager("extraction") 
        self.file_manager = FileManager(self.config.get_path_config())
        
    def extract_from_document(self, document_name: str):
        pdf_path = self.file_manager.find_file_or_raise(document_name)
        # ... extraction logic
```

---

## 🎉 **CONSOLIDATION COMPLETE**: Backend Utilities Moved

The following utilities have been successfully moved from `backend/common/` to `backend/core/`:

### **✅ Moved to backend.core:**
- **`AIUtils`** - OpenAI API interactions (Vision, Text, JSON parsing)
- **`JSONProcessor`** - Comprehensive JSON processing and sanitization  
- **`TextProcessor`** - Text processing (unicode cleaning, chunking, extraction)
- **`BasicPDFUtils`** - PDF text extraction and OCR capabilities

### **🏗️ Architecture Benefits:**
```
Before: Duplicated utilities across services
├── backend/common/ai_utils.py          ❌ 
├── backend/common/json_utils.py        ❌ 
├── backend/common/text_utils.py        ❌ 
├── backend/common/pdf_utils.py         ❌ 
├── some_service/similar_utils.py       ❌ DUPLICATE
└── another_service/openai_helper.py    ❌ DUPLICATE

After: Single source of truth
└── backend/core/                        ✅ SHARED
    ├── ai_utils.py       # All services use same OpenAI logic
    ├── json_utils.py     # All services use same JSON processing  
    ├── text_utils.py     # All services use same text processing
    └── pdf_processing.py # Consolidated PDF capabilities
```

### **📦 New Import Pattern:**
```python
# OLD (backend-specific)
from backend.common import AIUtils, TextProcessor

# NEW (shared across all services) 
from backend.core import AIUtils, TextProcessor, JSONProcessor, BasicPDFUtils
```

### **🔧 Configuration Hierarchy:**

Aithon Core SDK now serves as the **primary configuration system**:

```python
# ✅ PRIMARY: backend.core configuration (used by all services)
from backend.core import ConfigManager
config = ConfigManager("msb")  # or "fs", "backend", etc.

# ✅ SPECIALIZED: backend retains web-specific config extensions
# backend/common/config.py provides web-specific features while 
# delegating core functionality to backend.core
```

**Configuration Hierarchy:**
1. **`backend/core/config.py`** → Core SDK configuration (`.envvar` file, database, paths)
2. **`backend/common/config.py`** → Web-specific extensions (HTTP, FastAPI settings)  
3. **Service-specific configs** → Business logic configurations

---

## 📋 Migration Guide

### **Step 1: Replace File Operations**
```python
# OLD (duplicated in each service)
for data_folder in [self.msb_data_folder, self.general_data_folder]:
    potential_path = Path(data_folder) / document_name
    if potential_path.exists():
        pdf_path = str(potential_path)
        break

# NEW (shared via Aithon Core)
pdf_path = self.file_manager.find_file_or_raise(document_name)
```

### **Step 2: Replace Configuration Loading**
```python
# OLD (duplicated config parsing)
config = configparser.ConfigParser()
config.read(".env-local")
msb_data_folder = config.get("MSB", "msb_e2e_datafolder")

# NEW (shared config manager)
config = ConfigManager("msb") 
paths = config.get_path_config()
```

### **Step 3: Replace Status Checking**
```python
# OLD (duplicated file checking logic)
regular_file = os.path.join(openai_output_dir, f"{base_name}_page_{page_num + 1:03d}.md")
already_extracted = os.path.exists(regular_file)

# NEW (shared file operations)
already_extracted = self.file_manager.check_file_processed(document_name, page_num)
```

---

## 🎯 Future Services

When you add new microservices, they automatically get:

- ✅ **File discovery** - No need to rewrite PDF finding logic
- ✅ **Configuration management** - Automatic .env-local parsing  
- ✅ **PDF processing** - Common text extraction, image generation
- ✅ **Status checking** - Unified processing status tracking
- ✅ **Path management** - Consistent output folder structures

**Just import and use:**
```python
from backend.core import ConfigManager, FileManager, PDFDiscovery

# New service gets all the functionality instantly!
class NewMicroservice:
    def __init__(self):
        self.config = ConfigManager("new_service")
        self.file_manager = FileManager(self.config.get_path_config())
        # Ready to go! 🚀
```

---

## 🛡️ Testing

All core functionality is tested once in the SDK:
```python
# Test file operations
def test_file_discovery():
    assert file_manager.find_file("test.pdf") is not None
    
# Test PDF processing  
def test_pdf_extraction():
    processor = PDFProcessorFactory.create_processor()
    # ... test logic

# Test configuration
def test_config_loading():
    config = ConfigManager("test")
    # ... test logic
```

**Result**: All services inherit tested, reliable functionality! 🎉
