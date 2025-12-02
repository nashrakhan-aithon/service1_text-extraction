# S3 Integration Guide for Service 1

This guide outlines all the changes needed to integrate AWS S3 for storing extracted markdown files instead of local filesystem.

## Overview

Currently, extracted markdown files are saved to local filesystem at:
- Path: `{service1_output_folder}/{doc_id}/extracted_text/page_{page_num:04d}_{method}.md`

Service 1 now supports writing directly to S3. To enable it, simply set
`G_SERVICE1_OUTPUT_FOLDER` to an S3 URI (for example
`s3://my-bucket/service1-extracted-text`) and restart the containers. The
extraction service automatically uploads each extracted page to that bucket and
updates `datalake_text_uri` with the corresponding `s3://` path.

- Local Path Example: `{service1_output_folder}/{doc_id}/extracted_text/page_0001_fitz.md`
- S3 Path Example (when configured): `s3://{bucket_name}/{prefix}/{doc_id}/extracted_text/page_0001_fitz.md`

Make sure AWS credentials/permissions are available to the container (either via
standard AWS environment variables, IAM role, or mounted credentials).

---

The sections below capture the original design notes for reference.

---

## Step-by-Step Implementation

### Step 1: Add boto3 Dependency

**File:** `requirements.txt`

Add this line:
```python
boto3>=1.28.0
```

---

### Step 2: Create S3 Service Utility

**New File:** `backend/core/s3_service.py`

Create a new S3 service class with the following structure:

```python
import boto3
import logging
from typing import Optional, Dict, Any
from pathlib import Path
from botocore.exceptions import ClientError, BotoCoreError

logger = logging.getLogger(__name__)


class S3Service:
    """Service for handling S3 operations."""
    
    def __init__(
        self,
        bucket_name: str,
        region: str = "us-east-1",
        access_key_id: Optional[str] = None,
        secret_access_key: Optional[str] = None,
        prefix: Optional[str] = None
    ):
        """
        Initialize S3 service.
        
        Args:
            bucket_name: S3 bucket name
            region: AWS region (default: us-east-1)
            access_key_id: AWS access key (optional if using IAM role)
            secret_access_key: AWS secret key (optional if using IAM role)
            prefix: Optional prefix/folder path in S3
        """
        self.bucket_name = bucket_name
        self.region = region
        self.prefix = prefix or ""
        
        # Initialize S3 client
        if access_key_id and secret_access_key:
            self.s3_client = boto3.client(
                's3',
                region_name=region,
                aws_access_key_id=access_key_id,
                aws_secret_access_key=secret_access_key
            )
        else:
            # Use default credentials (IAM role, environment variables, or ~/.aws/credentials)
            self.s3_client = boto3.client('s3', region_name=region)
        
        logger.info(f"S3Service initialized for bucket: {bucket_name}, region: {region}")
    
    def upload_file(
        self,
        file_content: str,
        s3_key: str,
        content_type: str = "text/markdown"
    ) -> bool:
        """
        Upload file content to S3.
        
        Args:
            file_content: Content to upload (string)
            s3_key: S3 object key (path)
            content_type: MIME type (default: text/markdown)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Add prefix if specified
            full_key = f"{self.prefix}/{s3_key}" if self.prefix else s3_key
            # Remove leading slash if present
            full_key = full_key.lstrip('/')
            
            # Upload to S3
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=full_key,
                Body=file_content.encode('utf-8'),
                ContentType=content_type
            )
            
            logger.info(f"Successfully uploaded to S3: s3://{self.bucket_name}/{full_key}")
            return True
            
        except ClientError as e:
            logger.error(f"AWS ClientError uploading to S3: {str(e)}")
            return False
        except BotoCoreError as e:
            logger.error(f"AWS BotoCoreError uploading to S3: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error uploading to S3: {str(e)}")
            return False
    
    def get_s3_uri(self, s3_key: str) -> str:
        """
        Generate S3 URI for a given key.
        
        Args:
            s3_key: S3 object key (path)
            
        Returns:
            S3 URI (s3://bucket/key)
        """
        full_key = f"{self.prefix}/{s3_key}" if self.prefix else s3_key
        full_key = full_key.lstrip('/')
        return f"s3://{self.bucket_name}/{full_key}"
    
    def file_exists(self, s3_key: str) -> bool:
        """
        Check if file exists in S3.
        
        Args:
            s3_key: S3 object key (path)
            
        Returns:
            True if exists, False otherwise
        """
        try:
            full_key = f"{self.prefix}/{s3_key}" if self.prefix else s3_key
            full_key = full_key.lstrip('/')
            
            self.s3_client.head_object(Bucket=self.bucket_name, Key=full_key)
            return True
        except ClientError as e:
            if e.response['Error']['Code'] == '404':
                return False
            logger.error(f"Error checking S3 file existence: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error checking S3 file: {str(e)}")
            return False
```

---

### Step 3: Add S3 Configuration

**File:** `.envvar-service1`

Add these configuration variables in the `[COMMON]` section:

```ini
[COMMON]
# S3 Configuration
G_S3_BUCKET_NAME=your-bucket-name
G_S3_REGION=us-east-1
G_S3_ACCESS_KEY_ID=your-access-key-id
G_S3_SECRET_ACCESS_KEY=your-secret-access-key
G_S3_PREFIX=service1-extracted-text
```

**Note:** 
- If using IAM roles (e.g., in EC2/ECS), you can omit `G_S3_ACCESS_KEY_ID` and `G_S3_SECRET_ACCESS_KEY`
- If using environment variables, AWS SDK will automatically pick up `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY`

---

### Step 4: Modify DocumentTextExtractionService

**File:** `backend/services/document_text_extraction/services/document_text_extraction_service.py`

#### 4.1: Import S3Service

Add at the top:
```python
from backend.core.s3_service import S3Service
```

#### 4.2: Initialize S3 Service in __init__

In the `__init__` method (around line 55), add S3 initialization:

```python
# Initialize S3 service
s3_bucket = self.config.get_var(
    "G_S3_BUCKET_NAME",
    section="COMMON",
    fallback=None
)

if s3_bucket:
    s3_region = self.config.get_var(
        "G_S3_REGION",
        section="COMMON",
        fallback="us-east-1"
    )
    s3_access_key = self.config.get_var(
        "G_S3_ACCESS_KEY_ID",
        section="COMMON",
        fallback=None
    )
    s3_secret_key = self.config.get_var(
        "G_S3_SECRET_ACCESS_KEY",
        section="COMMON",
        fallback=None
    )
    s3_prefix = self.config.get_var(
        "G_S3_PREFIX",
        section="COMMON",
        fallback=None
    )
    
    self.s3_service = S3Service(
        bucket_name=s3_bucket,
        region=s3_region,
        access_key_id=s3_access_key,
        secret_access_key=s3_secret_key,
        prefix=s3_prefix
    )
    logger.info(f"S3 service initialized. Files will be saved to S3 bucket: {s3_bucket}")
else:
    self.s3_service = None
    logger.warning("S3 bucket not configured. Files will be saved to local filesystem.")
```

#### 4.3: Modify _save_extracted_content_to_service1_folder Method

Replace the method (lines 547-583) with:

```python
def _save_extracted_content_to_service1_folder(
    self, doc_id: str, extraction_result: Dict[str, Any]
) -> Dict[str, str]:
    """
    Save extracted text to S3 (if configured) or Service 1's local output folder.
    
    This method now supports both S3 and local filesystem storage.
    """
    import json
    
    file_paths = {}
    
    # Check if S3 is configured
    if self.s3_service:
        # Save to S3
        for page_num, page_data in extraction_result["pages"].items():
            method = page_data["method"]
            text = page_data["text"]
            
            # Create S3 key (path)
            s3_key = f"{doc_id}/extracted_text/page_{page_num:04d}_{method}.md"
            
            # Prepare file content
            file_content = f"# Page {page_num} - {method.upper()}\n\n{text}"
            
            # Upload to S3
            success = self.s3_service.upload_file(
                file_content=file_content,
                s3_key=s3_key,
                content_type="text/markdown"
            )
            
            if success:
                s3_uri = self.s3_service.get_s3_uri(s3_key)
                file_paths[page_num] = {
                    "text_file": s3_uri,
                }
                logger.info(f"Uploaded page {page_num} to S3: {s3_uri}")
            else:
                logger.error(f"Failed to upload page {page_num} to S3")
                # Optionally fall back to local storage
                # Or raise exception to fail the extraction
        
        logger.info(f"Saved extracted text for {doc_id} to S3 bucket: {self.s3_service.bucket_name}")
    else:
        # Fallback to local filesystem (existing behavior)
        doc_folder = self.service1_output_folder / doc_id
        doc_folder.mkdir(parents=True, exist_ok=True)
        
        extracted_text_dir = doc_folder / "extracted_text"
        extracted_text_dir.mkdir(exist_ok=True)
        
        for page_num, page_data in extraction_result["pages"].items():
            method = page_data["method"]
            text = page_data["text"]
            
            text_file = extracted_text_dir / f"page_{page_num:04d}_{method}.md"
            with open(text_file, "w", encoding="utf-8") as f:
                f.write(f"# Page {page_num} - {method.upper()}\n\n")
                f.write(text)
            
            file_paths[page_num] = {
                "text_file": str(text_file),
            }
        
        logger.info(f"Saved extracted text for {doc_id} to local folder: {extracted_text_dir}")
    
    return file_paths
```

#### 4.4: Update _update_datalake_text_uri Method Call

Modify the call around line 432-436:

```python
# Update datalake_text_uri in database
if self.s3_service:
    # Store S3 URI
    s3_text_uri = self.s3_service.get_s3_uri(f"{doc_id}/extracted_text")
    await self._update_datalake_text_uri(doc_id, s3_text_uri)
else:
    # Store local path (existing behavior)
    service1_text_path = self.service1_output_folder / doc_id / "extracted_text"
    await self._update_datalake_text_uri(doc_id, str(service1_text_path))
```

---

### Step 5: Error Handling & Validation

**Considerations:**

1. **S3 Upload Failures:**
   - Decide: Fail the extraction or fall back to local storage?
   - Add retry logic for transient failures
   - Log errors appropriately

2. **Credentials Validation:**
   - Test S3 connection on service initialization
   - Validate bucket exists and is accessible
   - Handle permission errors gracefully

3. **Network Issues:**
   - Add timeout configuration
   - Implement retry with exponential backoff
   - Consider async uploads for better performance

---

### Step 6: Testing

**Test Scenarios:**

1. ✅ S3 upload with valid credentials
2. ✅ S3 upload with invalid credentials (should fail gracefully)
3. ✅ S3 upload with network failure (retry logic)
4. ✅ Verify S3 URIs stored in database correctly
5. ✅ Verify files are accessible from S3
6. ✅ Fallback to local storage when S3 not configured
7. ✅ Multiple documents in parallel (concurrent uploads)

**Test Commands:**

```bash
# Check if file exists in S3
aws s3 ls s3://your-bucket/doc_id/extracted_text/

# Download a file to verify
aws s3 cp s3://your-bucket/doc_id/extracted_text/page_0001_fitz.md ./test.md

# Check database for stored URI
# Should show: s3://your-bucket/doc_id/extracted_text
```

---

### Step 7: Optional Enhancements

1. **Async S3 Uploads:**
   - Use `aioboto3` for async S3 operations
   - Better performance for parallel document processing

2. **S3 Path Configuration:**
   - Make path structure configurable
   - Support different naming conventions

3. **S3 Lifecycle Policies:**
   - Configure S3 lifecycle rules for cost optimization
   - Archive old files to Glacier

4. **Monitoring:**
   - Add CloudWatch metrics for upload success/failure
   - Track upload duration and file sizes

5. **File Listing:**
   - Add method to list all extracted files for a document
   - Useful for debugging and verification

---

## Summary of Files to Modify

1. ✅ `requirements.txt` - Add boto3
2. ✅ `backend/core/s3_service.py` - **NEW FILE** - S3 service utility
3. ✅ `.envvar-service1` - Add S3 configuration
4. ✅ `backend/services/document_text_extraction/services/document_text_extraction_service.py` - Modify save method and initialization

## Summary of Changes

- **Add:** S3 service class
- **Modify:** Save method to upload to S3
- **Modify:** Database URI storage to use S3 URIs
- **Add:** Configuration for S3 credentials and bucket
- **Add:** Error handling for S3 operations
- **Keep:** Fallback to local storage if S3 not configured

---

## Migration Strategy

If you want to migrate existing local files to S3:

1. Create a migration script to:
   - Read all existing local markdown files
   - Upload them to S3
   - Update database URIs
   - Optionally delete local files after verification

2. Run migration during maintenance window

---

## Security Considerations

1. **Credentials:**
   - Never commit credentials to git
   - Use IAM roles when possible (EC2/ECS)
   - Use AWS Secrets Manager for credentials
   - Rotate credentials regularly

2. **Bucket Permissions:**
   - Use least privilege IAM policies
   - Enable bucket versioning if needed
   - Enable bucket encryption (SSE-S3 or SSE-KMS)

3. **Network:**
   - Use VPC endpoints for S3 (if in AWS)
   - Enable S3 bucket policies for access control

---

## Cost Considerations

- **Storage:** ~$0.023 per GB/month (Standard storage)
- **Requests:** 
  - PUT requests: $0.005 per 1,000 requests
  - GET requests: $0.0004 per 1,000 requests
- **Data Transfer:** Free within same region, charges apply for cross-region

For typical usage (thousands of documents), costs should be minimal.

---

## Next Steps

1. Review this guide
2. Set up S3 bucket and IAM user/role
3. Add configuration to `.envvar-service1`
4. Implement S3 service class
5. Modify document extraction service
6. Test thoroughly
7. Deploy to staging environment
8. Monitor and verify
9. Deploy to production

