#!/usr/bin/env python3
"""
Service 1: Standalone API Server
================================
Starts Service 1 API server independently.
This version is for the standalone distribution package.
"""

import os
import sys
from pathlib import Path

# Add current directory to path (package root)
current_dir = Path(__file__).parent.resolve()
sys.path.insert(0, str(current_dir))

# Setup imports (if aithon_imports exists)
try:
    from aithon_imports import setup_imports
    setup_imports()
except ImportError:
    # If aithon_imports doesn't exist, continue without it
    pass

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Import Service 1 router
from backend.services.document_text_extraction.routers import document_text_extraction_router

# Create FastAPI app
app = FastAPI(
    title="Service 1: Document Text Extraction API",
    description="Standalone text extraction service - Extracts text from PDFs and saves .md files",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register Service 1 router
app.include_router(document_text_extraction_router, prefix="/api")

@app.get("/")
async def root():
    return {
        "service": "Service 1: Document Text Extraction",
        "version": "1.0.0",
        "status": "running",
        "endpoints": {
            "health": "/api/document-text-extraction/health",
            "extract": "/api/document-text-extraction/extract",
            "progress": "/api/document-text-extraction/progress/{batch_id}"
        }
    }

SERVICE1_PORT = int(os.getenv("SERVICE1_PORT", "8015"))

if __name__ == "__main__":
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=SERVICE1_PORT,
        reload=False
    )

