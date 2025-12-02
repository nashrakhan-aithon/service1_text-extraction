#!/bin/bash
# Service 1: Complete Test Script
# ================================
# Tests Service 1 with a PDF file
#
# Usage: ./test-service1.sh /path/to/your/document.pdf

set -e

PDF_PATH="$1"
if [ -z "$PDF_PATH" ]; then
    echo "❌ Usage: ./test-service1.sh /path/to/your/document.pdf"
    exit 1
fi

if [ ! -f "$PDF_PATH" ]; then
    echo "❌ PDF file not found: $PDF_PATH"
    exit 1
fi

echo "=========================================="
echo "Service 1: PDF Text Extraction Test"
echo "=========================================="
echo "PDF: $PDF_PATH"
echo ""

# Step 1: Get PDF information
echo "📄 Getting PDF information..."
PAGES=$(python3 -c "import fitz; doc = fitz.open('$PDF_PATH'); print(len(doc)); doc.close()" 2>/dev/null || echo "10")
SIZE=$(stat -f%z "$PDF_PATH" 2>/dev/null || stat -c%s "$PDF_PATH" 2>/dev/null || echo "1000000")
DOC_ID="DOC_test_$(date +%Y%m%d_%H%M%S)"
PDF_NAME=$(basename "$PDF_PATH")

echo "   Pages: $PAGES"
echo "   Size: $SIZE bytes"
echo "   Document ID: $DOC_ID"
echo ""

# Step 2: Check if Service 1 is running
echo "🔍 Checking Service 1 status..."
if ! docker ps --format "{{.Names}}" | grep -q "service1-api"; then
    echo "❌ Service 1 API is not running!"
    echo "   Start it with: docker-compose -f docker-compose-standalone.yml up -d"
    exit 1
fi

if ! docker ps --format "{{.Names}}" | grep -q "postgres-service1"; then
    echo "❌ Service 1 database is not running!"
    echo "   Start it with: docker-compose -f docker-compose-standalone.yml up -d"
    exit 1
fi

echo "   ✅ Service 1 is running"
echo ""

# Step 3: Copy PDF to container
echo "📤 Copying PDF to Service 1 datalake..."
docker exec service1-api mkdir -p "/app/datalake/$DOC_ID" || true
docker cp "$PDF_PATH" "service1-api:/app/datalake/$DOC_ID/source.pdf"
echo "   ✅ PDF copied to: /app/datalake/$DOC_ID/source.pdf"
echo ""

# Step 4: Add to database
echo "🗄️  Adding document to database..."
EXTRACTION_ID=$(docker exec postgres-service1-standalone psql -U postgres -d fcr001-text-extraction -t -c "
INSERT INTO doc_text_extraction_queue (
    doc_id, doc_name, file_ext, datalake_raw_uri,
    number_of_pages, file_size_bytes, is_active
) VALUES (
    '$DOC_ID', '$PDF_NAME', 'pdf',
    '/app/datalake/$DOC_ID/source.pdf',
    $PAGES, $SIZE, TRUE
) RETURNING extraction_id;
" 2>/dev/null | xargs)

if [ -z "$EXTRACTION_ID" ]; then
    echo "❌ Failed to add document to database"
    exit 1
fi

echo "   ✅ Added to database (Extraction ID: $EXTRACTION_ID)"
echo ""

# Step 5: Trigger extraction
echo "🚀 Triggering text extraction..."
RESPONSE=$(curl -s -X POST http://localhost:8015/api/document-text-extraction/extract \
  -H "Content-Type: application/json" \
  -d "{\"queue_ids\": [$EXTRACTION_ID]}")

SUCCESS=$(echo "$RESPONSE" | python3 -c "import sys, json; data=json.load(sys.stdin); print('true' if data.get('success') else 'false')" 2>/dev/null || echo "false")

if [ "$SUCCESS" != "true" ]; then
    echo "❌ Extraction failed!"
    echo "   Response: $RESPONSE"
    exit 1
fi

BATCH_ID=$(echo "$RESPONSE" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('batch_id', ''))" 2>/dev/null || echo "")

echo "   ✅ Extraction started (Batch ID: $BATCH_ID)"
echo ""

# Step 6: Wait for completion
echo "⏳ Waiting for extraction to complete..."
MAX_WAIT=60
WAITED=0
while [ $WAITED -lt $MAX_WAIT ]; do
    STATUS=$(docker exec postgres-service1-standalone psql -U postgres -d fcr001-text-extraction -t -c "
    SELECT text_extraction_status FROM doc_text_extraction_queue WHERE extraction_id = $EXTRACTION_ID;
    " 2>/dev/null | xargs)
    
    if [ "$STATUS" = "100" ]; then
        echo "   ✅ Extraction complete!"
        break
    elif [ "$STATUS" = "-1" ]; then
        echo "   ❌ Extraction failed!"
        docker exec postgres-service1-standalone psql -U postgres -d fcr001-text-extraction -t -c "
        SELECT error_message FROM doc_text_extraction_queue WHERE extraction_id = $EXTRACTION_ID;
        " 2>/dev/null
        exit 1
    fi
    
    echo -n "."
    sleep 2
    WAITED=$((WAITED + 2))
done

if [ "$STATUS" != "100" ]; then
    echo ""
    echo "⏳ Extraction still in progress (Status: $STATUS)"
    echo "   Check progress: curl http://localhost:8015/api/document-text-extraction/progress/$BATCH_ID"
    exit 0
fi

echo ""

# Step 7: Show results
echo "📊 Results:"
echo ""

# Database status
echo "Database Status:"
docker exec postgres-service1-standalone psql -U postgres -d fcr001-text-extraction -c "
SELECT 
    extraction_id AS \"ID\",
    doc_id AS \"Document ID\",
    text_extraction_status AS \"Status\",
    number_of_pages AS \"Pages\",
    text_extraction_duration_seconds AS \"Duration (s)\",
    datalake_text_uri AS \"Output Folder\"
FROM doc_text_extraction_queue 
WHERE extraction_id = $EXTRACTION_ID;
" 2>/dev/null

echo ""

# File count
FILE_COUNT=$(docker exec service1-api ls -1 "/app/output/$DOC_ID/extracted_text"/*.md 2>/dev/null | wc -l || echo "0")
echo "Extracted Files: $FILE_COUNT .md files"

# Show first page
echo ""
echo "First Page Preview:"
docker exec service1-api head -20 "/app/output/$DOC_ID/extracted_text/page_0001_fitz.md" 2>/dev/null || echo "   (File not found)"

echo ""
echo "=========================================="
echo "✅ Test Complete!"
echo "=========================================="
echo ""
echo "Extracted text files are in:"
echo "  /app/output/$DOC_ID/extracted_text/"
echo ""
echo "View files:"
echo "  docker exec service1-api ls -lh /app/output/$DOC_ID/extracted_text/"
echo "  docker exec service1-api cat /app/output/$DOC_ID/extracted_text/page_0001_fitz.md"

