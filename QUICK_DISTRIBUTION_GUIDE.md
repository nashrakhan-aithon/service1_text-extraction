# Service 1: Quick Distribution Guide

**For**: Creating and distributing Service 1 as a Docker image

---

## 🚀 **3-Step Distribution Process**

### **Step 1: Create Distribution Package**

```bash
cd backend/services/document_text_extraction
./create-distribution.sh
```

This creates: `service1-standalone-1.0.0.tar.gz`

### **Step 2: Give Package to Recipient**

Send them:
- `service1-standalone-1.0.0.tar.gz` (or the extracted folder)

### **Step 3: Recipient Runs It**

```bash
# Extract
tar -xzf service1-standalone-1.0.0.tar.gz
cd service1-standalone-1.0.0

# Start
docker-compose -f docker-compose-standalone.yml up -d

# Done!
```

---

## 📦 **What Recipient Gets**

### **Complete Package:**
- ✅ Docker Compose file (API + Database)
- ✅ Dockerfile (to build image)
- ✅ Configuration file
- ✅ Database schema
- ✅ Documentation
- ✅ Everything needed to run

### **No Dependencies Required:**
- ❌ No Python installation
- ❌ No PostgreSQL installation
- ❌ No system libraries
- ✅ Just Docker!

---

## 🎯 **Recipient Quick Start**

```bash
# 1. Extract
tar -xzf service1-standalone-1.0.0.tar.gz
cd service1-standalone-1.0.0

# 2. Start (builds image automatically)
docker-compose -f docker-compose-standalone.yml up -d

# 3. Verify
curl http://localhost:8015/api/document-text-extraction/health

# 4. Use it!
# Add documents to database, then extract text via API
```

---

## 📋 **Distribution Methods**

### **Method 1: Tar File (Recommended)**
```bash
# Create package
./create-distribution.sh

# Send: service1-standalone-1.0.0.tar.gz
```

### **Method 2: Docker Image**
```bash
# Build image
docker build -f Dockerfile -t service1:latest ../..

# Save image
docker save service1:latest | gzip > service1-image.tar.gz

# Send: service1-image.tar.gz + docker-compose-standalone.yml
```

### **Method 3: Docker Registry**
```bash
# Push to registry
docker tag service1:latest your-registry.com/service1:latest
docker push your-registry.com/service1:latest

# Recipient pulls
docker pull your-registry.com/service1:latest
```

---

## ✅ **What's Included**

- ✅ Complete Docker setup
- ✅ API server
- ✅ Database
- ✅ All dependencies
- ✅ Configuration
- ✅ Documentation

**Service 1 is ready to distribute!** 🎉

