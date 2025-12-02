# API Endpoints List

**Base URL:** `http://localhost:8015`

---

## Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/` | Root API information |
| `GET` | `/api/document-text-extraction/` | Service information |
| `GET` | `/api/document-text-extraction/health` | Health check |
| `POST` | `/api/document-text-extraction/extract` | Start text extraction |
| `GET` | `/api/document-text-extraction/progress/{batch_id}` | Get extraction progress |
| `GET` | `/api/docs` | Swagger UI documentation |
| `GET` | `/api/redoc` | ReDoc documentation |

---

## Quick Reference

### Root
- **GET** `/` - Returns service info and available endpoints

### Service Endpoints
- **GET** `/api/document-text-extraction/` - Service details
- **GET** `/api/document-text-extraction/health` - Health status
- **POST** `/api/document-text-extraction/extract` - Start extraction (requires `queue_ids` in body)
- **GET** `/api/document-text-extraction/progress/{batch_id}` - Track extraction progress

### Documentation
- **GET** `/api/docs` - Interactive API docs (Swagger)
- **GET** `/api/redoc` - Alternative API docs (ReDoc)

---

**Service Version:** 1.0.0  
**Port:** 8015

