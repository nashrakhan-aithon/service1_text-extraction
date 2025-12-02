# Service 1: Document Text Extraction - Standalone Service

**Status**: ✅ Completely Independent  
**Purpose**: Extract text from PDFs and save .md files  
**Architecture**: Standalone with own database container

---

## 🐳 **Docker Setup**

### **Service 1 Has Its Own PostgreSQL Container**

Service 1 uses a **completely separate Docker container** for its database:
- **Container Name**: `postgres-service1-standalone`
- **Port**: `5433` (different from main container's 5432)
- **Database**: `fcr001-text-extraction`
- **Data Directory**: `~/projects/aithon/aithon_output/postgres-service1`

### **Start Service 1 Database:**

```bash
cd backend/services/document_text_extraction
docker-compose up -d
```

### **Stop Service 1 Database:**

```bash
cd backend/services/document_text_extraction
docker-compose down
```

### **Verify Container:**

```bash
docker ps --filter "name=postgres-service1"
```

---

## 📋 **Configuration**

### **Config File**: `.envvar-service1`

Service 1 uses its own configuration file (not `.envvar`):
- Database: `fcr001-text-extraction`
- Port: `5433` (separate from main container)
- Output Folder: `service1-extracted-text/`

---

## 🗄️ **Database**

### **Service 1 Database Container:**

- **Container**: `postgres-service1-standalone`
- **Database**: `fcr001-text-extraction`
- **Table**: `doc_text_extraction_queue`
- **Port**: `5433`

### **Connection:**

```bash
# Connect to Service 1 database
docker exec postgres-service1-standalone psql -U postgres -d fcr001-text-extraction

# Or from host
psql -h localhost -p 5433 -U postgres -d fcr001-text-extraction
```

---

## 🚀 **Usage**

### **1. Start Service 1 Database:**

```bash
cd backend/services/document_text_extraction
docker-compose up -d
```

### **2. Apply Schema:**

```bash
docker exec postgres-service1-standalone psql -U postgres -d fcr001-text-extraction \
  -f /path/to/schema.sql
```

### **3. Run Service 1:**

```bash
python temp/test_service_1.py <extraction_id>
```

---

## 📦 **Docker Image Creation**

Service 1 can be packaged as a standalone Docker image:

```dockerfile
# Dockerfile for Service 1 (example)
FROM python:3.10
WORKDIR /app
COPY backend/services/document_text_extraction/ .
COPY .envvar-service1 .
# ... install dependencies, etc.
```

**Benefits:**
- ✅ No dependencies on main system
- ✅ Own database container
- ✅ Own configuration
- ✅ Can be tested independently

---

## 🔄 **Complete Independence**

Service 1 is completely independent:
- ✅ Own Docker container (`postgres-service1-standalone`)
- ✅ Own database (`fcr001-text-extraction`)
- ✅ Own config file (`.envvar-service1`)
- ✅ Own output folder (`service1-extracted-text/`)
- ✅ No dependencies on main system

---

## 📚 **Files**

- `docker-compose.yml` - Service 1's database container
- `.envvar-service1` - Service 1's configuration
- `database/schemas/document_text_extraction/` - Database schema

---

**Service 1 is ready to be packaged as a standalone Docker image!** 🎉

