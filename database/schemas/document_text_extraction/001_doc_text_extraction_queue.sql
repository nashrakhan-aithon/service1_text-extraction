-- Service 1: Document Text Extraction Queue
-- ===========================================
-- 
-- This is a COMPLETELY SEPARATE database for Service 1.
-- Service 1 does NOT touch the existing fcr001-devdb database.
-- 
-- Database: fcr001-text-extraction
-- Purpose: Track text extraction operations independently

-- ============================================================================
-- TABLE: doc_text_extraction_queue
-- ============================================================================
-- Tracks text extraction operations for Service 1
-- This table is completely independent from doc_queue_manager

CREATE TABLE IF NOT EXISTS doc_text_extraction_queue (
    -- Primary Key
    extraction_id BIGSERIAL PRIMARY KEY,
    
    -- Document Identification
    doc_id VARCHAR(32) NOT NULL,
    doc_name VARCHAR(500),
    file_ext VARCHAR(10) NOT NULL DEFAULT 'pdf',
    
    -- Source Information
    source_uri TEXT,
    datalake_raw_uri TEXT,
    datalake_text_uri TEXT,
    
    -- Processing Status
    text_extraction_status INTEGER DEFAULT NULL CHECK (
        text_extraction_status IS NULL 
        OR text_extraction_status = -1  -- Failed
        OR (text_extraction_status >= 0 AND text_extraction_status <= 100)  -- Progress percentage
    ),
    
    -- Processing Metrics
    number_of_pages INTEGER DEFAULT 0 CHECK (number_of_pages >= 0),
    extracted_pages INTEGER DEFAULT 0 CHECK (extracted_pages >= 0),
    text_extraction_duration_seconds INTEGER,
    
    -- Error Tracking
    error_message TEXT,
    last_error_message TEXT,
    
    -- File Information
    file_size_bytes BIGINT DEFAULT 0 CHECK (file_size_bytes >= 0),
    password TEXT,  -- PDF password if needed
    
    -- Processing Lock
    is_processing BOOLEAN DEFAULT FALSE,
    processing_started_at TIMESTAMPTZ,
    
    -- Lifecycle
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    extracted_at TIMESTAMPTZ,  -- When extraction completed
    last_processed_at TIMESTAMPTZ
);

-- ============================================================================
-- INDEXES
-- ============================================================================

-- Unique constraint on doc_id
CREATE UNIQUE INDEX IF NOT EXISTS uq_doc_text_extraction_queue_doc_id 
    ON doc_text_extraction_queue (doc_id);

-- Index for finding documents ready for extraction
CREATE INDEX IF NOT EXISTS ix_doc_text_extraction_queue_status 
    ON doc_text_extraction_queue (text_extraction_status) 
    WHERE is_active = TRUE;

-- Index for finding documents that need extraction
CREATE INDEX IF NOT EXISTS ix_doc_text_extraction_queue_pending 
    ON doc_text_extraction_queue (is_active, text_extraction_status) 
    WHERE is_active = TRUE AND (text_extraction_status IS NULL OR text_extraction_status < 100);

-- Index for finding completed extractions
CREATE INDEX IF NOT EXISTS ix_doc_text_extraction_queue_completed 
    ON doc_text_extraction_queue (text_extraction_status, extracted_at) 
    WHERE text_extraction_status = 100;

-- Index for processing lock
CREATE INDEX IF NOT EXISTS ix_doc_text_extraction_queue_processing 
    ON doc_text_extraction_queue (is_processing, processing_started_at) 
    WHERE is_processing = TRUE;

-- Index for timestamps
CREATE INDEX IF NOT EXISTS ix_doc_text_extraction_queue_created_at 
    ON doc_text_extraction_queue (created_at DESC);

-- ============================================================================
-- COMMENTS
-- ============================================================================

COMMENT ON TABLE doc_text_extraction_queue IS 
    'Service 1: Text extraction queue - COMPLETELY SEPARATE from main doc_queue_manager table';

COMMENT ON COLUMN doc_text_extraction_queue.extraction_id IS 
    'Primary key for text extraction operations';

COMMENT ON COLUMN doc_text_extraction_queue.doc_id IS 
    'Unique document identifier (matches doc_id from main system, but stored independently)';

COMMENT ON COLUMN doc_text_extraction_queue.text_extraction_status IS 
    'Extraction status: NULL=not started, 0-100=progress percentage, 100=complete, -1=failed';

COMMENT ON COLUMN doc_text_extraction_queue.datalake_text_uri IS 
    'Path to extracted text folder containing .md files';

