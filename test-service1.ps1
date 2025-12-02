# Service 1: Complete Test Script for Windows
# ============================================
# Tests Service 1 with a PDF file - does everything automatically
#
# Usage:
#   .\test-service1.ps1 "C:\path\to\your\document.pdf"
#   .\test-service1.ps1 "C:\path\to\your\document.pdf" -PdfPassword "actual-password"

param(
    [Parameter(Mandatory=$true)]
    [string]$PdfPath,

    [Parameter(Mandatory=$false)]
    [string]$PdfPassword
)

$servicePort = $env:SERVICE1_PORT
if (-not $servicePort -or $servicePort.Trim().Length -eq 0) {
    $servicePort = 8015
}
$apiBase = "http://localhost:$servicePort"
$serviceHealthUrl = "$apiBase/api/document-text-extraction/health"
$extractUrl = "$apiBase/api/document-text-extraction/extract"

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "Service 1: PDF Text Extraction Test" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "PDF: $PdfPath" -ForegroundColor Yellow
if ($PdfPassword -and $PdfPassword.Trim().Length -gt 0) {
    Write-Host "Password: (provided)" -ForegroundColor Yellow
} else {
    Write-Host "Password: (not provided - service default will be used)" -ForegroundColor Yellow
}
Write-Host ""

# Step 1: Verify PDF exists
if (-not (Test-Path $PdfPath)) {
    Write-Host "❌ ERROR: PDF file not found: $PdfPath" -ForegroundColor Red
    exit 1
}

# Step 2: Get PDF information
Write-Host "[1/6] Getting PDF information..." -ForegroundColor Yellow
$fileSize = (Get-Item $PdfPath).Length
$fileName = Split-Path -Leaf $PdfPath
$docId = "DOC_test_$(Get-Date -Format 'yyyyMMdd_HHmmss')"

Write-Host "   File: $fileName" -ForegroundColor Cyan
Write-Host "   Size: $fileSize bytes" -ForegroundColor Cyan
Write-Host "   Document ID: $docId" -ForegroundColor Cyan
Write-Host ""

# Step 3: Check if Service 1 is running
Write-Host "[2/6] Checking Service 1 status..." -ForegroundColor Yellow
$apiRunning = docker ps --format "{{.Names}}" | Select-String -Pattern "service1-api"
$dbRunning = docker ps --format "{{.Names}}" | Select-String -Pattern "postgres-service1"

if (-not $apiRunning) {
    Write-Host "❌ ERROR: Service 1 API is not running!" -ForegroundColor Red
    Write-Host "   Start it with: docker-compose -f docker-compose-standalone.yml up -d" -ForegroundColor Yellow
    exit 1
}

if (-not $dbRunning) {
    Write-Host "❌ ERROR: Service 1 database is not running!" -ForegroundColor Red
    Write-Host "   Start it with: docker-compose -f docker-compose-standalone.yml up -d" -ForegroundColor Yellow
    exit 1
}

Write-Host "   ✅ Service 1 is running" -ForegroundColor Green
Write-Host ""

# Step 4: Copy PDF to container
Write-Host "[3/6] Copying PDF to container..." -ForegroundColor Yellow
docker exec service1-api mkdir -p "/app/datalake/$docId" | Out-Null
docker cp $PdfPath "service1-api:/app/datalake/$docId/source.pdf"

if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ ERROR: Failed to copy PDF to container" -ForegroundColor Red
    exit 1
}

Write-Host "   ✅ PDF copied to container" -ForegroundColor Green
Write-Host ""

# Step 5: Add to database
Write-Host "[4/6] Adding PDF to database..." -ForegroundColor Yellow
$passwordValue = "NULL"
if ($PdfPassword -and $PdfPassword.Trim().Length -gt 0) {
    $escapedPassword = $PdfPassword.Replace("'", "''")
    $passwordValue = "'$escapedPassword'"
}
$sql = "INSERT INTO doc_text_extraction_queue (doc_id, doc_name, file_ext, datalake_raw_uri, number_of_pages, file_size_bytes, is_active, password) VALUES ('$docId', '$fileName', 'pdf', '/app/datalake/$docId/source.pdf', 10, $fileSize, TRUE, $passwordValue) RETURNING extraction_id;"
$result = docker exec postgres-service1-standalone psql -U postgres -d fcr001-text-extraction -t -c $sql

if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ ERROR: Failed to add PDF to database" -ForegroundColor Red
    exit 1
}

# Extract just the ID number (remove "INSERT 0 1" and other text)
# The result might be "1" or "1  INSERT 0 1" - we need just the first number
$extractionId = ($result -split "`n" | Where-Object { $_ -match '^\s*\d+\s*$' } | Select-Object -First 1).Trim()
if (-not $extractionId) {
    # Try to extract first number from the result
    if ($result -match '\d+') {
        $extractionId = $matches[0]
    }
}

if (-not $extractionId -or $extractionId -eq "") {
    Write-Host "❌ ERROR: Could not extract extraction_id from database response" -ForegroundColor Red
    Write-Host "   Response: $result" -ForegroundColor Yellow
    exit 1
}

# Ensure it's a valid integer
try {
    $extractionIdInt = [int]$extractionId
} catch {
    Write-Host "❌ ERROR: Invalid extraction_id: $extractionId" -ForegroundColor Red
    exit 1
}

Write-Host "   ✅ Added to database" -ForegroundColor Green
Write-Host "   Extraction ID: $extractionId" -ForegroundColor Cyan
Write-Host ""

# Step 6: Trigger extraction
Write-Host "[5/6] Triggering text extraction..." -ForegroundColor Yellow
$body = @{
    queue_ids = @($extractionIdInt)
} | ConvertTo-Json -Compress

try {
    $response = Invoke-RestMethod -Uri $extractUrl `
        -Method POST `
        -ContentType "application/json" `
        -Body $body
    
    $responseData = $response
    
    if ($responseData.success) {
        Write-Host "   ✅ Extraction started" -ForegroundColor Green
        Write-Host "   Batch ID: $($responseData.batch_id)" -ForegroundColor Cyan
    } else {
        Write-Host "   ⚠️  Extraction may have failed" -ForegroundColor Yellow
    }
} catch {
    Write-Host "❌ ERROR: Failed to trigger extraction" -ForegroundColor Red
    Write-Host "   Error: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}

Write-Host ""

# Step 7: Monitor progress
Write-Host "[6/6] Monitoring extraction progress..." -ForegroundColor Yellow
$batchId = $responseData.batch_id
$maxWait = 300  # 5 minutes max
$elapsed = 0
$interval = 5   # Check every 5 seconds

while ($elapsed -lt $maxWait) {
    Start-Sleep -Seconds $interval
    $elapsed += $interval
    
    try {
        $progressResponse = Invoke-RestMethod -Uri "$apiBase/api/document-text-extraction/progress/$batchId" -UseBasicParsing
        $progress = $progressResponse.progress_percentage
        
        Write-Host "   Progress: $progress% ($($progressResponse.processed_documents)/$($progressResponse.total_documents) documents, $($progressResponse.processed_pages)/$($progressResponse.total_pages) pages)" -ForegroundColor Cyan
        
        if ($progress -eq 100) {
            Write-Host ""
            Write-Host "✅ Extraction completed!" -ForegroundColor Green
            break
        }
        
        if ($progressResponse.status -eq "failed") {
            Write-Host ""
            Write-Host "❌ Extraction failed!" -ForegroundColor Red
            Write-Host "   Errors: $($progressResponse.errors | ConvertTo-Json)" -ForegroundColor Red
            exit 1
        }
    } catch {
        # Progress endpoint might not be ready yet
        Write-Host "   Waiting for extraction to start..." -ForegroundColor Yellow
    }
}

if ($elapsed -ge $maxWait) {
    Write-Host ""
    Write-Host "⏱️  Timeout: Extraction is taking longer than expected" -ForegroundColor Yellow
    Write-Host "   Check progress manually: curl $apiBase/api/document-text-extraction/progress/$batchId" -ForegroundColor Cyan
}

Write-Host ""

# Step 8: Show results
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "Results" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan

# Check database status
$statusResult = docker exec postgres-service1-standalone psql -U postgres -d fcr001-text-extraction -t -c "SELECT text_extraction_status, extracted_pages, number_of_pages, error_message FROM doc_text_extraction_queue WHERE extraction_id = $extractionId;"
$statusParts = $statusResult.Trim() -split '\|'
$extractionStatus = $statusParts[0].Trim()
$extractedPages = $statusParts[1].Trim()
$totalPages = $statusParts[2].Trim()
$errorMsg = $statusParts[3].Trim()

Write-Host "Extraction Status: $extractionStatus%" -ForegroundColor $(if ($extractionStatus -eq "100") { "Green" } else { "Yellow" })
Write-Host "Extracted Pages: $extractedPages / $totalPages" -ForegroundColor Cyan

if ($errorMsg -and $errorMsg -ne "") {
    Write-Host "Error: $errorMsg" -ForegroundColor Red
}

Write-Host ""

# List extracted files
Write-Host "Extracted Files:" -ForegroundColor Cyan
$files = docker exec service1-api ls -1 "/app/output/$docId/extracted_text/" 2>$null
if ($files) {
    $files | ForEach-Object {
        Write-Host "   $_" -ForegroundColor White
    }
} else {
    Write-Host "   No files found yet (extraction may still be in progress)" -ForegroundColor Yellow
}

Write-Host ""

# Step 9: Show classification summary from Service 2
Write-Host "Classification Summary (Service 2):" -ForegroundColor Cyan
$classificationQuery = @"
SELECT coalesce(
    json_build_object(
        'status', doc_classification_status,
        'prediction', aithondoctypeid_ai,
        'probabilities', aithondoctypeid_prob_ai
    )::text,
    ''
)
FROM doc_text_extraction_queue
WHERE extraction_id = $extractionId;
"@

$classificationRaw = docker exec postgres-service1-standalone psql -U postgres -d fcr001-text-extraction -t -A -c $classificationQuery
$classificationJson = $classificationRaw.Trim()

$classificationData = $null
if ($classificationJson -and $classificationJson.Length -gt 0) {
    try {
        $classificationData = $classificationJson | ConvertFrom-Json
    } catch {
        Write-Host "   ⚠️  Unable to parse classification JSON: $classificationJson" -ForegroundColor Yellow
    }
}

if ($classificationData -and $classificationData.status) {
    $classificationStatus = $classificationData.status
    $prediction = $classificationData.prediction
    $probabilities = $classificationData.probabilities

    Write-Host "   Status: $classificationStatus" -ForegroundColor Cyan
    if ($prediction) {
        Write-Host "   Prediction: $prediction" -ForegroundColor Green
    }

    if ($probabilities) {
        $probList = $probabilities.psobject.Properties |
            Sort-Object -Property Value -Descending

        Write-Host "   Probabilities:" -ForegroundColor Cyan
        foreach ($prob in $probList) {
            $percentage = [math]::Round([double]$prob.Value * 100, 2)
            $color = if ($prob.Name -eq $prediction) { "Green" } else { "White" }
            Write-Host ("      {0,-8}: {1,6}%" -f $prob.Name, $percentage) -ForegroundColor $color
        }
    }
} else {
    Write-Host "   (No classification results yet)" -ForegroundColor Yellow
}

Write-Host ""

# Show how to view extracted text
Write-Host "To view extracted text:" -ForegroundColor Cyan
Write-Host "   docker exec service1-api cat /app/output/$docId/extracted_text/page_001.md" -ForegroundColor White

Write-Host ""
Write-Host "✅ Test complete!" -ForegroundColor Green

