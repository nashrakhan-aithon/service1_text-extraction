# Service 1 API Endpoints Documentation

Complete list of all API endpoints for Service 1 (Document Text Extraction Service).

---

## 🌐 Base URL

- **Local Development:** `http://localhost:8015`
- **API Prefix:** `/api`
- **Service Prefix:** `/document-text-extraction`

**Full Base Path:** `http://localhost:8015/api/document-text-extraction`

---

## 📋 All Endpoints

### 1. **Root Endpoint** (Service Info)
**GET** `/api/document-text-extraction/`

**Description:** Returns service information and available endpoints.

**Response:**
```json
{
  "service": "Document Text Extraction Service (Service 1)",
  "version": "1.0.0",
  "status": "operational",
  "description": "Extracts text from PDFs and saves .md files. Embedding and classification handled by Service 2.",
  "service_first_architecture": true,
  "available_endpoints": {
    "service_root": "/document-text-extraction/",
    "service_health": "/document-text-extraction/health",
    "progress": "/document-text-extraction/progress/{batch_id}",
    "api_documentation": "/api/docs"
  }
}
```

**Example Request:**
```bash
curl http://localhost:8015/api/document-text-extraction/
```

---

### 2. **Health Check**
**GET** `/api/document-text-extraction/health`

**Description:** Health check endpoint to verify service is running.

**Response:**
```json
{
  "service": "document_text_extraction",
  "status": "healthy",
  "capabilities": [
    "pdf_download",
    "ocr_and_text_extraction",
    "text_file_storage"
  ]
}
```

**Example Request:**
```bash
curl http://localhost:8015/api/document-text-extraction/health
```

**Status Codes:**
- `200 OK` - Service is healthy

---

### 3. **Extract Text** (Main Endpoint)
**POST** `/api/document-text-extraction/extract`

**Description:** 
- Extracts text from PDFs for selected queue items
- Runs asynchronously in background
- Returns immediately with batch_id for progress tracking
- Saves extracted text as .md files (currently to local filesystem, will be S3 after integration)

**Request Body:**
```json
{
  "queue_ids": [1, 2, 3],
  "batch_id": "optional-batch-id"
}
```

**Request Parameters:**
- `queue_ids` (required, List[int]): List of extraction_id values from `doc_text_extraction_queue` table
- `batch_id` (optional, str): Optional batch ID for progress tracking. If not provided, one will be generated.

**Response:**
```json
{
  "success": true,
  "message": "Text extraction started for 3 documents",
  "processed_count": 0,
  "failed_count": 0,
  "batch_id": "batch-1234567890",
  "results": []
}
```

**Response Fields:**
- `success` (bool): Whether the extraction was started successfully
- `message` (str): Status message
- `processed_count` (int): Number of documents processed (0 initially, updated via progress endpoint)
- `failed_count` (int): Number of documents that failed (0 initially)
- `batch_id` (str): Batch ID for tracking progress
- `results` (List): Empty initially, populated via progress endpoint

**Example Request:**
```bash
curl -X POST http://localhost:8015/api/document-text-extraction/extract \
  -H "Content-Type: application/json" \
  -d '{
    "queue_ids": [1, 2, 3]
  }'
```

**Example with batch_id:**
```bash
curl -X POST http://localhost:8015/api/document-text-extraction/extract \
  -H "Content-Type: application/json" \
  -d '{
    "queue_ids": [1, 2, 3],
    "batch_id": "my-custom-batch-123"
  }'
```

**Status Codes:**
- `200 OK` - Extraction started successfully
- `500 Internal Server Error` - Failed to start extraction

**Notes:**
- This endpoint returns immediately - extraction runs in background
- Use the `batch_id` to track progress via the progress endpoint
- Extraction process:
  1. Downloads/accesses PDF file
  2. Extracts text from all pages (PyMuPDF/OCR)
  3. Saves .md files (one per page)
  4. Updates `text_extraction_status = 100` in database
  5. Updates `datalake_text_uri` with path to extracted text folder

---

### 4. **Get Progress**
**GET** `/api/document-text-extraction/progress/{batch_id}`

**Description:** 
- Get real-time progress for an active text extraction batch
- Poll this endpoint to track extraction progress
- Returns detailed progress information including current document, stage, and page counts

**Path Parameters:**
- `batch_id` (required, str): Batch ID returned from extract endpoint

**Response:**
```json
{
  "batch_id": "batch-1234567890",
  "status": "processing",
  "total_documents": 3,
  "processed_documents": 1,
  "total_pages": 150,
  "processed_pages": 50,
  "progress_percentage": 33,
  "current_document": "DOC_test_123",
  "current_stage": "extracting_text",
  "current_operation": "Extracting text from PDF pages using PyMuPDF/OCR",
  "started_at": 1234567890.123,
  "completed_at": null,
  "results": [
    {
      "doc_id": "DOC_test_123",
      "success": true,
      "status": "success",
      "total_pages": 50,
      "processed_pages": 50,
      "file_paths": {
        "1": {
          "text_file": "/path/to/page_0001_fitz.md"
        },
        "2": {
          "text_file": "/path/to/page_0002_fitz.md"
        }
      },
      "duration_seconds": 45
    }
  ],
  "errors": []
}
```

**Response Fields:**
- `batch_id` (str): Batch ID
- `status` (str): Current status - `"processing"`, `"completed"`, or `"failed"`
- `total_documents` (int): Total number of documents in batch
- `processed_documents` (int): Number of documents completed
- `total_pages` (int): Total pages across all documents
- `processed_pages` (int): Number of pages processed
- `progress_percentage` (int): Progress percentage (0-100)
- `current_document` (str, optional): Currently processing document ID
- `current_stage` (str, optional): Current processing stage
  - `"initializing"` - Setting up extraction
  - `"downloading_pdf"` - Accessing PDF file
  - `"extracting_text"` - Extracting text from pages
  - `"completed"` - Extraction complete
- `current_operation` (str, optional): Detailed operation description
- `started_at` (float, optional): Unix timestamp when batch started
- `completed_at` (float, optional): Unix timestamp when batch completed
- `results` (List[Dict]): List of document processing results
  - Each result contains:
    - `doc_id`: Document ID
    - `success`: Whether extraction succeeded
    - `status`: Status string
    - `total_pages`: Total pages in document
    - `processed_pages`: Pages processed
    - `file_paths`: Dictionary mapping page numbers to file paths
    - `duration_seconds`: Processing duration
- `errors` (List): List of any errors encountered

**Example Request:**
```bash
curl http://localhost:8015/api/document-text-extraction/progress/batch-1234567890
```

**Status Codes:**
- `200 OK` - Progress information returned
- If batch not found, returns completed state with empty data (stops polling gracefully)

**Polling Strategy:**
```bash
# Poll every 2 seconds until status is "completed"
while true; do
  response=$(curl -s http://localhost:8015/api/document-text-extraction/progress/batch-1234567890)
  status=$(echo $response | jq -r '.status')
  echo "Status: $status"
  
  if [ "$status" = "completed" ] || [ "$status" = "failed" ]; then
    break
  fi
  
  sleep 2
done
```

---

### 5. **API Documentation (Swagger UI)**
**GET** `/api/docs`

**Description:** Interactive API documentation (Swagger UI)

**Access:** Open in browser: `http://localhost:8015/api/docs`

**Features:**
- View all endpoints
- Test endpoints directly from browser
- See request/response schemas
- Try out API calls

---

### 6. **API Documentation (ReDoc)**
**GET** `/api/redoc`

**Description:** Alternative API documentation (ReDoc format)

**Access:** Open in browser: `http://localhost:8015/api/redoc`

---

### 7. **Root API Endpoint**
**GET** `/`

**Description:** Root endpoint for the entire API

**Response:**
```json
{
  "service": "Service 1: Document Text Extraction",
  "version": "1.0.0",
  "status": "running",
  "endpoints": {
    "health": "/api/document-text-extraction/health",
    "extract": "/api/document-text-extraction/extract",
    "progress": "/api/document-text-extraction/progress/{batch_id}"
  }
}
```

**Example Request:**
```bash
curl http://localhost:8015/
```

---

## 📊 Complete Endpoint Summary

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| GET | `/` | Root API info | No |
| GET | `/api/document-text-extraction/` | Service info | No |
| GET | `/api/document-text-extraction/health` | Health check | No |
| POST | `/api/document-text-extraction/extract` | Start text extraction | No |
| GET | `/api/document-text-extraction/progress/{batch_id}` | Get progress | No |
| GET | `/api/docs` | Swagger UI | No |
| GET | `/api/redoc` | ReDoc UI | No |

---

## 🔄 Typical Workflow

### Step 1: Check Health
```bash
curl http://localhost:8015/api/document-text-extraction/health
```

### Step 2: Start Extraction
```bash
curl -X POST http://localhost:8015/api/document-text-extraction/extract \
  -H "Content-Type: application/json" \
  -d '{"queue_ids": [1, 2, 3]}'
```

**Response:**
```json
{
  "batch_id": "batch-1234567890",
  ...
}
```

### Step 3: Poll Progress
```bash
curl http://localhost:8015/api/document-text-extraction/progress/batch-1234567890
```

**Keep polling until `status: "completed"`**

### Step 4: Check Results
Results are included in the progress response when status is "completed".

---

## 📝 Request/Response Examples

### Extract Text - Full Example

**Request:**
```bash
curl -X POST http://localhost:8015/api/document-text-extraction/extract \
  -H "Content-Type: application/json" \
  -d '{
    "queue_ids": [1, 2, 3],
    "batch_id": "my-batch-2024-01-15"
  }'
```

**Response:**
```json
{
  "success": true,
  "message": "Text extraction started for 3 documents",
  "processed_count": 0,
  "failed_count": 0,
  "batch_id": "my-batch-2024-01-15",
  "results": []
}
```

### Progress - Full Example

**Request:**
```bash
curl http://localhost:8015/api/document-text-extraction/progress/my-batch-2024-01-15
```

**Response (Processing):**
```json
{
  "batch_id": "my-batch-2024-01-15",
  "status": "processing",
  "total_documents": 3,
  "processed_documents": 1,
  "total_pages": 150,
  "processed_pages": 50,
  "progress_percentage": 33,
  "current_document": "DOC_test_123",
  "current_stage": "extracting_text",
  "current_operation": "Extracting text from PDF pages using PyMuPDF/OCR",
  "started_at": 1705320000.123,
  "completed_at": null,
  "results": [
    {
      "doc_id": "DOC_test_123",
      "success": true,
      "status": "success",
      "total_pages": 50,
      "processed_pages": 50,
      "file_paths": {
        "1": {"text_file": "/app/output/DOC_test_123/extracted_text/page_0001_fitz.md"},
        "2": {"text_file": "/app/output/DOC_test_123/extracted_text/page_0002_fitz.md"}
      },
      "duration_seconds": 45
    }
  ],
  "errors": []
}
```

**Response (Completed):**
```json
{
  "batch_id": "my-batch-2024-01-15",
  "status": "completed",
  "total_documents": 3,
  "processed_documents": 3,
  "total_pages": 150,
  "processed_pages": 150,
  "progress_percentage": 100,
  "current_document": null,
  "current_stage": "completed",
  "current_operation": "Text extraction completed - ready for Service 2 (embedding/classification)",
  "started_at": 1705320000.123,
  "completed_at": 1705320100.456,
  "results": [
    {
      "doc_id": "DOC_test_123",
      "success": true,
      "status": "success",
      "total_pages": 50,
      "processed_pages": 50,
      "file_paths": {...},
      "duration_seconds": 45
    },
    {
      "doc_id": "DOC_test_456",
      "success": true,
      "status": "success",
      "total_pages": 75,
      "processed_pages": 75,
      "file_paths": {...},
      "duration_seconds": 60
    },
    {
      "doc_id": "DOC_test_789",
      "success": true,
      "status": "success",
      "total_pages": 25,
      "processed_pages": 25,
      "file_paths": {...},
      "duration_seconds": 20
    }
  ],
  "errors": []
}
```

---

## ⚠️ Important Notes

1. **Asynchronous Processing:** The `/extract` endpoint returns immediately. Extraction runs in background.

2. **Progress Tracking:** Use the `batch_id` from extract response to poll progress endpoint.

3. **File Paths:** Currently returns local file paths. After S3 integration, will return S3 URIs (e.g., `s3://bucket-name/doc_id/extracted_text/page_0001_fitz.md`).

4. **Database:** Service 1 uses its own database (`fcr001-text-extraction`) and table (`doc_text_extraction_queue`).

5. **Queue IDs:** `queue_ids` in extract request refer to `extraction_id` column in `doc_text_extraction_queue` table.

6. **Error Handling:** Errors are included in progress response `errors` array and individual document results.

---

## 🔍 Testing Endpoints

### Quick Test Script
```bash
#!/bin/bash

BASE_URL="http://localhost:8015/api/document-text-extraction"

# 1. Health check
echo "=== Health Check ==="
curl -s $BASE_URL/health | jq

# 2. Service info
echo -e "\n=== Service Info ==="
curl -s $BASE_URL/ | jq

# 3. Start extraction
echo -e "\n=== Starting Extraction ==="
RESPONSE=$(curl -s -X POST $BASE_URL/extract \
  -H "Content-Type: application/json" \
  -d '{"queue_ids": [1]}')

BATCH_ID=$(echo $RESPONSE | jq -r '.batch_id')
echo "Batch ID: $BATCH_ID"

# 4. Poll progress
echo -e "\n=== Polling Progress ==="
while true; do
  PROGRESS=$(curl -s $BASE_URL/progress/$BATCH_ID)
  STATUS=$(echo $PROGRESS | jq -r '.status')
  PERCENT=$(echo $PROGRESS | jq -r '.progress_percentage')
  echo "Status: $STATUS | Progress: $PERCENT%"
  
  if [ "$STATUS" = "completed" ] || [ "$STATUS" = "failed" ]; then
    echo -e "\n=== Final Results ==="
    echo $PROGRESS | jq
    break
  fi
  
  sleep 2
done
```

---

## 📚 Additional Resources

- **Swagger UI:** `http://localhost:8015/api/docs`
- **ReDoc:** `http://localhost:8015/api/redoc`
- **Service Port:** `8015` (configurable in `start_api.py`)
- **Database:** PostgreSQL on port `5432` (default)

---

## 🔄 After S3 Integration

Once S3 integration is complete, the following will change:

1. **File Paths in Response:**
   - **Before:** `/app/output/DOC_123/extracted_text/page_0001_fitz.md`
   - **After:** `s3://bucket-name/DOC_123/extracted_text/page_0001_fitz.md`

2. **Database `datalake_text_uri` field:**
   - **Before:** `/app/output/DOC_123/extracted_text`
   - **After:** `s3://bucket-name/DOC_123/extracted_text`

3. **No local files:** Files will only exist in S3 (unless fallback is configured)

---

**Last Updated:** 2024-01-15
**Service Version:** 1.0.0

