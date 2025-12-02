# How to Verify You Have the Correct Package

## ⚠️ **Critical: You Must Delete Old Package First**

The error you're seeing means you still have the **OLD package** extracted. You MUST delete it completely before extracting the new one.

---

## ✅ **Step-by-Step Fix (Windows)**

### **1. Delete OLD Package Completely**

**In Command Prompt or PowerShell:**
```cmd
cd C:\Users\NashraKhan\Desktop\project\doc-classify
rmdir /s /q service1-standalone-1.0.0
```

**Or manually:**
- Delete the entire `service1-standalone-1.0.0` folder
- Make sure it's completely gone

---

### **2. Download NEW Package**

- File: `service1-standalone-1.0.0.tar.gz`
- Location: `backend/services/document_text_extraction/service1-standalone-1.0.0.tar.gz`
- **IMPORTANT**: Make sure you download the NEWEST version (created after the Dockerfile fix)

---

### **3. Extract NEW Package**

```cmd
tar -xzf service1-standalone-1.0.0.tar.gz
cd service1-standalone-1.0.0
```

---

### **4. Verify You Have the CORRECT Dockerfile**

**Check line 23:**
```cmd
findstr /n "COPY requirements.txt" Dockerfile
```

**Should show:**
```
23:COPY requirements.txt ./
```

**NOT:**
```
22:COPY backend/services/document_text_extraction/requirements.txt ./requirements.txt
```

**Check line 33:**
```cmd
findstr /n "COPY start_api.py" Dockerfile
```

**Should show:**
```
33:COPY start_api.py ./
```

**NOT:**
```
51:COPY backend/services/document_text_extraction/start_api.py ./backend/services/document_text_extraction/start_api.py
```

---

### **5. If Verification Fails**

If you see the OLD paths (`backend/services/document_text_extraction/...`), then:
1. You still have the OLD package
2. Delete everything and download the NEW package again
3. Make sure you're downloading from the correct location

---

## 🔍 **Quick Verification Script (Windows)**

Create a file `verify-package.bat`:

```batch
@echo off
echo Verifying package...
findstr /n "COPY requirements.txt" Dockerfile | findstr "23:COPY requirements.txt ./"
if %errorlevel% equ 0 (
    echo ✅ Dockerfile is CORRECT!
    findstr /n "COPY start_api.py" Dockerfile | findstr "33:COPY start_api.py ./"
    if %errorlevel% equ 0 (
        echo ✅ All paths are CORRECT!
        echo.
        echo Package is ready to use!
    ) else (
        echo ❌ start_api.py path is WRONG - you have OLD package
    )
) else (
    echo ❌ requirements.txt path is WRONG - you have OLD package
    echo.
    echo Please delete this folder and download the NEW package!
)
pause
```

Run it:
```cmd
verify-package.bat
```

---

## 📋 **What the CORRECT Dockerfile Should Look Like**

**Lines 22-24:**
```dockerfile
# Copy requirements and install Python dependencies
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
```

**Lines 29-33:**
```dockerfile
# Copy all files (backend/, aithon_imports.py, project_root.py, start_api.py)
COPY backend/ ./backend/
COPY aithon_imports.py ./
COPY project_root.py ./
COPY start_api.py ./
```

**Line 51:**
```dockerfile
CMD ["python", "start_api.py"]
```

---

## ❌ **What the WRONG Dockerfile Looks Like**

**Lines 22-23:**
```dockerfile
COPY backend/services/document_text_extraction/requirements.txt ./requirements.txt
```

**Line 51:**
```dockerfile
COPY backend/services/document_text_extraction/start_api.py ./backend/services/document_text_extraction/start_api.py
```

**If you see these paths, you have the OLD package!**

---

## 🎯 **Summary**

1. ✅ Delete OLD `service1-standalone-1.0.0` folder completely
2. ✅ Download NEW `service1-standalone-1.0.0.tar.gz` package
3. ✅ Extract it fresh
4. ✅ Verify Dockerfile has `COPY requirements.txt ./` (not `backend/services/...`)
5. ✅ Run `docker-compose up -d`

---

**The new package is correct - make sure you delete the old one first!** ✅

