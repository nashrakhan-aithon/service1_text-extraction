# Service 1: Document Text Extraction Database Schema

**Database**: `fcr001-text-extraction`  
**Purpose**: Completely separate database for Service 1  
**Status**: Independent from main `fcr001-devdb` database

## Overview

This database is **completely isolated** from the main system:
- ✅ Service 1 writes ONLY to this database
- ✅ Service 1 does NOT touch `fcr001-devdb`
- ✅ Service 1 is treated as a separate project

## Tables

### `doc_text_extraction_queue`
Tracks all text extraction operations for Service 1.

## Setup

### 1. Create Database
```bash
docker exec postgres-docdownload-persistent psql -U postgres -c "CREATE DATABASE \"fcr001-text-extraction\";"
```

### 2. Apply Schema
```bash
docker exec postgres-docdownload-persistent psql -U postgres -d fcr001-text-extraction -f database/schemas/document_text_extraction/001_doc_text_extraction_queue.sql
```

### 3. Verify
```bash
docker exec postgres-docdownload-persistent psql -U postgres -d fcr001-text-extraction -c "\dt"
```

## Configuration

Add to `.envvar`:
```ini
[POSTGRES_SERVICE1]
G_POSTGRES_SERVICE1_DATABASE=fcr001-text-extraction
G_POSTGRES_SERVICE1_HOST=localhost
G_POSTGRES_SERVICE1_PORT=5432
G_POSTGRES_SERVICE1_USER=postgres
G_POSTGRES_SERVICE1_PASSWORD=postgres
```

## Migration Notes

- Service 1 will NOT update `doc_queue_manager` in `fcr001-devdb`
- Service 1 is completely independent
- Integration with Service 2 will be handled separately (if needed)

