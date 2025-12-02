# Service 1: Distribution Package Guide

**Purpose**: Complete guide for creating and distributing Service 1 as a standalone Docker package.

---

## 📦 **What to Include in Distribution**

### **Required Files:**

1. **Dockerfile** - Image build instructions
2. **docker-compose-standalone.yml** - Complete setup (API + Database)
3. **.envvar-service1** - Configuration file
4. **requirements.txt** - Python dependencies
5. **database/schemas/document_text_extraction/** - Database schema
6. **README.md** - User instructions
7. **BUILD_AND_DISTRIBUTE.md** - Build instructions

### **Optional Files:**

- Example PDF files for testing
- Sample API requests
- Troubleshooting guide

---

## 🚀 **Distribution Methods**

### **Method 1: Docker Image + Compose File**

**Best for**: Users familiar with Docker

**Package Contents:**
```
service1-package/
├── docker-compose-standalone.yml
├── Dockerfile
├── .envvar-service1
├── requirements.txt
├── database/
│   └── schemas/
│       └── document_text_extraction/
│           └── 001_doc_text_extraction_queue.sql
└── README.md
```

**Instructions for Recipient:**
```bash
# Build and run
docker-compose -f docker-compose-standalone.yml up -d
```

---

### **Method 2: Pre-built Docker Image**

**Best for**: Users who just want to run it

**Steps:**
1. Build image: `docker build -t service1:latest .`
2. Save image: `docker save service1:latest | gzip > service1-image.tar.gz`
3. Distribute: Image file + docker-compose-standalone.yml

**Instructions for Recipient:**
```bash
# Load image
docker load < service1-image.tar.gz

# Run
docker-compose -f docker-compose-standalone.yml up -d
```

---

### **Method 3: Docker Registry**

**Best for**: Enterprise/cloud deployments

**Steps:**
1. Push to registry: `docker push your-registry.com/service1:latest`
2. Share registry URL and credentials

**Instructions for Recipient:**
```bash
# Pull image
docker pull your-registry.com/service1:latest

# Run
docker-compose -f docker-compose-standalone.yml up -d
```

---

## 📋 **Recipient Requirements**

### **System Requirements:**

- Docker Engine 20.10+
- Docker Compose 2.0+
- 2GB RAM minimum
- 5GB disk space

### **No Additional Requirements:**

- ✅ No Python installation needed
- ✅ No PostgreSQL installation needed
- ✅ No system dependencies needed
- ✅ Everything runs in containers

---

## 🔧 **Configuration Options**

### **Port Customization:**

Edit `docker-compose-standalone.yml`:
```yaml
ports:
  - "8016:8015"  # Change host port if 8015 is taken
  - "5434:5432"  # Change database port if 5433 is taken
```

### **Password Customization:**

Edit `docker-compose-standalone.yml`:
```yaml
environment:
  - G_POSTGRES_SERVICE1_PASSWORD=your-secure-password
```

---

## 🧪 **Testing Before Distribution**

### **1. Build Test:**

```bash
docker build -f Dockerfile -t service1:test ../..
```

### **2. Run Test:**

```bash
docker-compose -f docker-compose-standalone.yml up -d
```

### **3. Functionality Test:**

```bash
# Health check
curl http://localhost:8015/api/document-text-extraction/health

# Add document
docker exec postgres-service1-standalone psql -U postgres -d fcr001-text-extraction -c "INSERT INTO ..."

# Extract text
curl -X POST http://localhost:8015/api/document-text-extraction/extract ...
```

### **4. Clean Test:**

```bash
# Stop and remove
docker-compose -f docker-compose-standalone.yml down -v

# Rebuild and test again
docker-compose -f docker-compose-standalone.yml up -d
```

---

## 📝 **Distribution Checklist**

- [ ] All files included
- [ ] Dockerfile tested
- [ ] docker-compose tested
- [ ] Documentation complete
- [ ] Example usage provided
- [ ] Troubleshooting guide included
- [ ] Version tagged
- [ ] Tested on clean system

---

## 🎯 **Quick Distribution Script**

```bash
#!/bin/bash
# create-distribution.sh

VERSION="1.0.0"
PACKAGE_NAME="service1-standalone-${VERSION}"

# Create package directory
mkdir -p ${PACKAGE_NAME}

# Copy required files
cp docker-compose-standalone.yml ${PACKAGE_NAME}/
cp Dockerfile ${PACKAGE_NAME}/
cp .envvar-service1 ${PACKAGE_NAME}/
cp requirements.txt ${PACKAGE_NAME}/
cp -r ../../database/schemas/document_text_extraction ${PACKAGE_NAME}/database/schemas/
cp README.md ${PACKAGE_NAME}/
cp BUILD_AND_DISTRIBUTE.md ${PACKAGE_NAME}/

# Create archive
tar -czf ${PACKAGE_NAME}.tar.gz ${PACKAGE_NAME}/

echo "✅ Distribution package created: ${PACKAGE_NAME}.tar.gz"
```

---

**Service 1 is ready for distribution!** 🎉

