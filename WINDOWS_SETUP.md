# Service 1: Windows Setup Guide
## =============================

This guide helps you set up and run Service 1 on **Windows**.

---

## ✅ **Prerequisites**

1. **Docker Desktop for Windows** - [Download here](https://www.docker.com/products/docker-desktop)
2. **Git Bash** or **WSL2** (for running shell scripts)
3. **A PDF file** to test with

---

## 🚀 **Quick Start (Windows)**

### **Step 1: Extract Package**

**Using Git Bash:**
```bash
tar -xzf service1-standalone-1.0.0.tar.gz
cd service1-standalone-1.0.0
```

**Using PowerShell:**
```powershell
# Extract using 7-Zip or WinRAR
# Or use WSL:
wsl tar -xzf service1-standalone-1.0.0.tar.gz
wsl cd service1-standalone-1.0.0
```

---

### **Step 2: Start Service 1**

**Using Docker Desktop:**
```bash
docker-compose -f docker-compose-standalone.yml up -d
```

**Or using PowerShell:**
```powershell
docker-compose -f docker-compose-standalone.yml up -d
```

**Expected Output:**
```
[+] Building X.Xs
[+] Running 2/2
 ✔ Container postgres-service1-standalone  Started
 ✔ Container service1-api                  Started
```

---

### **Step 3: Verify Service is Running**

**Check containers:**
```bash
docker ps
```

**Check API health:**
```bash
curl http://localhost:8015/api/document-text-extraction/health
```

**Or in PowerShell:**
```powershell
Invoke-WebRequest -Uri http://localhost:8015/api/document-text-extraction/health
```

**Expected Response:**
```json
{"status": "healthy", "service": "Service 1: Document Text Extraction"}
```

---

## 🧪 **Testing with PDF (Windows)**

### **Method 1: Using Git Bash Script**

```bash
# Make script executable (if needed)
chmod +x test-service1.sh

# Run test
./test-service1.sh "C:/path/to/your/document.pdf"
```

### **Method 2: Manual Steps (PowerShell)**

**1. Copy PDF to Service 1:**
```powershell
docker exec service1-api mkdir -p /app/datalake/DOC_test_123
docker cp "C:\path\to\document.pdf" service1-api:/app/datalake/DOC_test_123/source.pdf
```

**2. Add to Database:**
```powershell
docker exec postgres-service1-standalone psql -U postgres -d fcr001-text-extraction -c "INSERT INTO doc_text_extraction_queue (doc_id, doc_name, file_ext, datalake_raw_uri, number_of_pages, file_size_bytes, is_active) VALUES ('DOC_test_123', 'document.pdf', 'pdf', '/app/datalake/DOC_test_123/source.pdf', 10, 1000000, TRUE) RETURNING extraction_id;"
```

**3. Trigger Extraction:**
```powershell
Invoke-WebRequest -Uri http://localhost:8015/api/document-text-extraction/extract -Method POST -ContentType "application/json" -Body '{"queue_ids": [1]}'
```

**4. Check Results:**
```powershell
# Database status
docker exec postgres-service1-standalone psql -U postgres -d fcr001-text-extraction -c "SELECT text_extraction_status FROM doc_text_extraction_queue WHERE extraction_id = 1;"

# Extracted files
docker exec service1-api ls -lh /app/output/DOC_test_123/extracted_text/
```

---

## 🔧 **Troubleshooting (Windows)**

### **Issue: "Cannot find file specified"**

**Error:**
```
resolve : CreateFile C:\Users\...\backend: The system cannot find the file specified.
```

**Solution:**
The package is now **self-contained**. Make sure you're running `docker-compose` from **inside** the extracted package directory:

```bash
cd service1-standalone-1.0.0
docker-compose -f docker-compose-standalone.yml up -d
```

---

### **Issue: Port Already in Use**

**Error:**
```
Error: bind: address already in use
```

**Solution:**
Change ports in `docker-compose-standalone.yml`:

```yaml
ports:
  - "8016:8015"  # Change 8015 to 8016
  - "5434:5432"  # Change 5433 to 5434
```

---

### **Issue: Docker Desktop Not Running**

**Error:**
```
Cannot connect to the Docker daemon
```

**Solution:**
1. Start **Docker Desktop** application
2. Wait for it to fully start (whale icon in system tray)
3. Try again

---

### **Issue: Permission Denied (Scripts)**

**Error:**
```
Permission denied: ./test-service1.sh
```

**Solution (Git Bash):**
```bash
chmod +x test-service1.sh
./test-service1.sh
```

**Solution (PowerShell):**
Use manual steps instead (see Method 2 above).

---

## 📁 **Windows Path Notes**

- **Use forward slashes** in Git Bash: `C:/path/to/file.pdf`
- **Use backslashes** in PowerShell: `C:\path\to\file.pdf`
- **Docker paths** always use forward slashes: `/app/datalake/DOC_123/source.pdf`

---

## ✅ **Verification Checklist**

- [ ] Docker Desktop is running
- [ ] Containers are up: `docker ps`
- [ ] API responds: `curl http://localhost:8015/api/document-text-extraction/health`
- [ ] Database is accessible: `docker exec postgres-service1-standalone psql -U postgres -d fcr001-text-extraction -c "\dt"`
- [ ] Can copy files: `docker cp test.pdf service1-api:/app/datalake/`

---

## 🆘 **Need Help?**

1. Check container logs:
   ```bash
   docker logs service1-api
   docker logs postgres-service1-standalone
   ```

2. Check Docker Desktop logs

3. Verify all prerequisites are installed

---

**Service 1 is now ready to use on Windows!** 🎉

