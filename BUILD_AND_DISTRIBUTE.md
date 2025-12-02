# Service 1: Build and Distribute Docker Image

**Purpose**: Create a standalone Docker image that can be distributed and run on any system.

---

## 📦 **Building the Docker Image**

### **Option 1: Build from Project Root (Recommended)**

```bash
cd backend/services/document_text_extraction
docker build -f Dockerfile -t service1:latest ../..
```

### **Option 2: Build with docker-compose**

```bash
cd backend/services/document_text_extraction
docker-compose -f docker-compose-standalone.yml build
```

---

## 🚀 **Running the Complete Service 1**

### **Start Everything (API + Database):**

```bash
cd backend/services/document_text_extraction
docker-compose -f docker-compose-standalone.yml up -d
```

### **Check Status:**

```bash
docker-compose -f docker-compose-standalone.yml ps
```

### **View Logs:**

```bash
# API logs
docker logs service1-api

# Database logs
docker logs postgres-service1-standalone
```

### **Stop Everything:**

```bash
docker-compose -f docker-compose-standalone.yml down
```

---

## 📤 **Distributing the Image**

### **Method 1: Save as Tar File**

```bash
# Save image to file
docker save service1:latest | gzip > service1-image.tar.gz

# On recipient's machine, load the image
docker load < service1-image.tar.gz
```

### **Method 2: Push to Docker Registry**

```bash
# Tag for registry
docker tag service1:latest your-registry.com/service1:latest

# Push to registry
docker push your-registry.com/service1:latest

# Recipient pulls
docker pull your-registry.com/service1:latest
```

### **Method 3: Export Complete Setup**

```bash
# Create distribution package
tar -czf service1-distribution.tar.gz \
    docker-compose-standalone.yml \
    Dockerfile \
    .envvar-service1 \
    database/schemas/document_text_extraction/ \
    README.md \
    BUILD_AND_DISTRIBUTE.md
```

---

## 📋 **Recipient Setup Instructions**

### **1. Extract Files:**

```bash
tar -xzf service1-distribution.tar.gz
cd service1-distribution
```

### **2. Build Image (if needed):**

```bash
docker build -f Dockerfile -t service1:latest .
```

### **3. Start Services:**

```bash
docker-compose -f docker-compose-standalone.yml up -d
```

### **4. Verify:**

```bash
# Check API health
curl http://localhost:8015/api/document-text-extraction/health

# Check database
docker exec postgres-service1-standalone psql -U postgres -d fcr001-text-extraction -c "\dt"
```

---

## 🔧 **Configuration**

### **Environment Variables (in docker-compose-standalone.yml):**

```yaml
environment:
  - G_POSTGRES_SERVICE1_HOST=postgres-service1
  - G_POSTGRES_SERVICE1_PORT=5432
  - G_POSTGRES_SERVICE1_USER=postgres
  - G_POSTGRES_SERVICE1_PASSWORD=postgres
  - G_POSTGRES_SERVICE1_DATABASE=fcr001-text-extraction
  - G_SERVICE1_OUTPUT_FOLDER=/app/output
  - G_AITHON_DATALAKE=/app/datalake
```

### **Ports:**

- **API**: `8015` (host) → `8015` (container)
- **Database**: `5433` (host) → `5432` (container)

---

## 📊 **What's Included**

### **Containers:**
- ✅ `service1-api` - Service 1 API server
- ✅ `postgres-service1-standalone` - PostgreSQL database

### **Volumes:**
- ✅ `service1-db-data` - Database persistence
- ✅ `service1-output` - Extracted text files
- ✅ `service1-datalake` - Source PDF files

### **Networks:**
- ✅ `service1-network` - Isolated network

---

## 🧪 **Testing the Distribution**

### **1. Build Image:**

```bash
docker build -f Dockerfile -t service1:latest ../..
```

### **2. Start Services:**

```bash
docker-compose -f docker-compose-standalone.yml up -d
```

### **3. Test API:**

```bash
# Health check
curl http://localhost:8015/api/document-text-extraction/health

# Extract text (example)
curl -X POST http://localhost:8015/api/document-text-extraction/extract \
  -H "Content-Type: application/json" \
  -d '{"queue_ids": [1]}'
```

### **4. Check Database:**

```bash
docker exec postgres-service1-standalone psql -U postgres -d fcr001-text-extraction \
  -c "SELECT * FROM doc_text_extraction_queue;"
```

---

## 📝 **Distribution Checklist**

- [ ] Dockerfile created
- [ ] docker-compose-standalone.yml created
- [ ] requirements.txt included
- [ ] .envvar-service1 included
- [ ] Database schema included
- [ ] README.md with instructions
- [ ] Tested build process
- [ ] Tested run process
- [ ] Documentation complete

---

## 🎯 **Quick Start for Recipient**

```bash
# 1. Extract
tar -xzf service1-distribution.tar.gz
cd service1-distribution

# 2. Start
docker-compose -f docker-compose-standalone.yml up -d

# 3. Verify
curl http://localhost:8015/api/document-text-extraction/health

# Done! Service 1 is running.
```

---

**Service 1 is ready for distribution as a standalone Docker image!** 🎉

