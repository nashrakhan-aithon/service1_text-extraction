# Service 1: Testing Guide for Recipients

**Purpose**: Step-by-step guide to test Service 1 with your own PDF files

---

## 🚀 **Step 1: Extract and Start Service 1**

```bash
# Extract the package
tar -xzf service1-standalone-1.0.0.tar.gz
cd service1-standalone-1.0.0

# Start Service 1 (API + Database)
docker-compose -f docker-compose-standalone.yml up -d

# Wait a few seconds for services to start
sleep 10

# Verify services are running
docker ps --filter "name=service1"
```

**Expected Output:**
```
NAMES                          STATUS
service1-api                   Up (healthy)
postgres-service1-standalone   Up (healthy)
```

---

## ✅ **Step 2: Verify API is Running**

```bash
# Test health endpoint
curl http://localhost:8015/api/document-text-extraction/health

# Expected response:
# {"service":"document_text_extraction","status":"healthy","capabilities":[...]}
```

---

## 📄 **Step 3: Prepare Your PDF File**

### **Option A: Copy PDF to a Location Service 1 Can Access**

```bash
# Create a folder for your test PDFs
mkdir -p ~/test-pdfs

# Copy your PDF file there
cp /path/to/your/document.pdf ~/test-pdfs/test.pdf

# Note the full path
echo "PDF path: $(readlink -f ~/test-pdfs/test.pdf)"
```

### **Option B: Use Docker Volume (Recommended)**

The docker-compose file creates a `service1-datalake` volume. You can mount your PDF folder:

**Edit `docker-compose-standalone.yml`:**
```yaml
volumes:
  - service1-datalake:/app/datalake
  # Add this line to mount your local folder:
  - ~/test-pdfs:/app/datalake  # Your PDFs folder
```

Then restart:
```bash
docker-compose -f docker-compose-standalone.yml down
docker-compose -f docker-compose-standalone.yml up -d
```

---

## 🗄️ **Step 4: Add PDF to Service 1 Database**

### **Get PDF Information:**

```bash
# Get PDF page count (if you have Python)
python3 -c "import fitz; doc = fitz.open('~/test-pdfs/test.pdf'); print(f'Pages: {len(doc)}'); doc.close()"

# Or manually count pages, or use any PDF tool
```

### **Add Document to Database:**

```bash
# Connect to Service 1 database
docker exec -it postgres-service1-standalone psql -U postgres -d fcr001-text-extraction

# Insert your document
INSERT INTO doc_text_extraction_queue (
    doc_id,
    doc_name,
    file_ext,
    source_uri,
    datalake_raw_uri,
    number_of_pages,
    file_size_bytes,
    is_active
) VALUES (
    'DOC_test_yourname_20251119',  -- Change to unique ID
    'test.pdf',                     -- Your PDF filename
    'pdf',
    '/path/to/your/test.pdf',      -- Original location
    '/app/datalake/DOC_test_yourname_20251119/source.pdf',  -- Where Service 1 will look
    10,                             -- Number of pages (update this)
    1000000,                        -- File size in bytes (update this)
    TRUE
) RETURNING extraction_id, doc_id;
```

**Note the `extraction_id` from the response!**

**Exit database:**
```sql
\q
```

---

## 📤 **Step 5: Copy PDF to Service 1 Datalake**

```bash
# Create document folder in datalake
docker exec service1-api mkdir -p /app/datalake/DOC_test_yourname_20251119

# Copy your PDF into the container
docker cp ~/test-pdfs/test.pdf service1-api:/app/datalake/DOC_test_yourname_20251119/source.pdf

# Verify it's there
docker exec service1-api ls -lh /app/datalake/DOC_test_yourname_20251119/
```

---

## 🔄 **Step 6: Trigger Text Extraction via API**

```bash
# Replace <extraction_id> with the ID from Step 4
EXTRACTION_ID=1  # Use your actual extraction_id

# Trigger extraction
curl -X POST http://localhost:8015/api/document-text-extraction/extract \
  -H "Content-Type: application/json" \
  -d "{\"queue_ids\": [$EXTRACTION_ID]}"

# Expected response:
# {"success":true,"message":"Processed 1 documents: 1 successful, 0 failed",...}
```

---

## ✅ **Step 7: Check Progress**

```bash
# Get the batch_id from the response above, then:
BATCH_ID="batch_1234567890_1"  # Use actual batch_id from response

# Check progress
curl http://localhost:8015/api/document-text-extraction/progress/$BATCH_ID

# Expected response shows progress percentage
```

---

## 📁 **Step 8: Verify Results**

### **Check Database:**

```bash
docker exec postgres-service1-standalone psql -U postgres -d fcr001-text-extraction -c "
SELECT 
    extraction_id,
    doc_id,
    text_extraction_status,
    number_of_pages,
    datalake_text_uri
FROM doc_text_extraction_queue 
WHERE extraction_id = $EXTRACTION_ID;
"
```

**Expected:**
- `text_extraction_status` = `100` (complete)
- `datalake_text_uri` = path to extracted text folder

### **Check Extracted Files:**

```bash
# List extracted .md files
docker exec service1-api ls -lh /app/output/DOC_test_yourname_20251119/extracted_text/

# View first page content
docker exec service1-api cat /app/output/DOC_test_yourname_20251119/extracted_text/page_0001_fitz.md
```

---

## 🧪 **Complete Test Script**

Save this as `test-service1.sh`:

```bash
#!/bin/bash
# Complete Service 1 Test Script

PDF_PATH="$1"
if [ -z "$PDF_PATH" ]; then
    echo "Usage: ./test-service1.sh /path/to/your/document.pdf"
    exit 1
fi

echo "=== Service 1 Testing ==="
echo "PDF: $PDF_PATH"

# Step 1: Get PDF info
echo "Getting PDF information..."
PAGES=$(python3 -c "import fitz; doc = fitz.open('$PDF_PATH'); print(len(doc)); doc.close()" 2>/dev/null || echo "10")
SIZE=$(stat -f%z "$PDF_PATH" 2>/dev/null || stat -c%s "$PDF_PATH" 2>/dev/null || echo "1000000")
DOC_ID="DOC_test_$(date +%Y%m%d_%H%M%S)"

echo "Pages: $PAGES, Size: $SIZE bytes"

# Step 2: Copy PDF to container
echo "Copying PDF to Service 1..."
docker exec service1-api mkdir -p /app/datalake/$DOC_ID
docker cp "$PDF_PATH" service1-api:/app/datalake/$DOC_ID/source.pdf

# Step 3: Add to database
echo "Adding to database..."
EXTRACTION_ID=$(docker exec postgres-service1-standalone psql -U postgres -d fcr001-text-extraction -t -c "
INSERT INTO doc_text_extraction_queue (
    doc_id, doc_name, file_ext, datalake_raw_uri,
    number_of_pages, file_size_bytes, is_active
) VALUES (
    '$DOC_ID', '$(basename "$PDF_PATH")', 'pdf',
    '/app/datalake/$DOC_ID/source.pdf',
    $PAGES, $SIZE, TRUE
) RETURNING extraction_id;
" | xargs)

echo "Extraction ID: $EXTRACTION_ID"

# Step 4: Trigger extraction
echo "Triggering extraction..."
RESPONSE=$(curl -s -X POST http://localhost:8015/api/document-text-extraction/extract \
  -H "Content-Type: application/json" \
  -d "{\"queue_ids\": [$EXTRACTION_ID]}")

echo "Response: $RESPONSE"

# Step 5: Wait and check status
echo "Waiting for extraction to complete..."
sleep 5

STATUS=$(docker exec postgres-service1-standalone psql -U postgres -d fcr001-text-extraction -t -c "
SELECT text_extraction_status FROM doc_text_extraction_queue WHERE extraction_id = $EXTRACTION_ID;
" | xargs)

echo "Status: $STATUS (100 = complete)"

# Step 6: Show results
if [ "$STATUS" = "100" ]; then
    echo "✅ Extraction complete!"
    echo "Files:"
    docker exec service1-api ls -1 /app/output/$DOC_ID/extracted_text/*.md 2>/dev/null | wc -l
    echo "files created"
else
    echo "⏳ Extraction in progress or failed. Check logs:"
    echo "docker logs service1-api"
fi
```

**Usage:**
```bash
chmod +x test-service1.sh
./test-service1.sh /path/to/your/document.pdf
```

---

## 📋 **Quick Test Checklist**

- [ ] Service 1 started (`docker ps` shows both containers)
- [ ] API health check passes (`curl http://localhost:8015/api/document-text-extraction/health`)
- [ ] PDF file copied to datalake
- [ ] Document added to database
- [ ] Extraction triggered via API
- [ ] Status = 100 in database
- [ ] .md files created in output folder

---

## 🔍 **Troubleshooting**

### **API Not Responding:**
```bash
# Check logs
docker logs service1-api

# Restart
docker-compose -f docker-compose-standalone.yml restart service1-api
```

### **Database Connection Error:**
```bash
# Check database is running
docker ps --filter "name=postgres-service1"

# Check connection
docker exec postgres-service1-standalone psql -U postgres -d fcr001-text-extraction -c "SELECT 1;"
```

### **PDF Not Found:**
```bash
# Verify PDF is in container
docker exec service1-api ls -lh /app/datalake/DOC_*/source.pdf

# Check datalake_raw_uri in database matches actual location
```

---

## 📚 **Example: Complete Test Flow**

```bash
# 1. Start Service 1
docker-compose -f docker-compose-standalone.yml up -d

# 2. Test with your PDF
./test-service1.sh ~/Downloads/my-document.pdf

# 3. Check results
docker exec postgres-service1-standalone psql -U postgres -d fcr001-text-extraction \
  -c "SELECT doc_id, text_extraction_status FROM doc_text_extraction_queue;"

# 4. View extracted text
docker exec service1-api cat /app/output/DOC_*/extracted_text/page_0001_fitz.md
```

---

**Service 1 is ready to test with any PDF file!** 🎉

