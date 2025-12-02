# Service 1: Quick Start Guide for Recipients

**Welcome!** This guide will help you test Service 1 with your own PDF files.

---

## 🚀 **Quick Start (3 Steps)**

### **1. Start Service 1:**

```bash
docker-compose -f docker-compose-standalone.yml up -d
```

Wait 10 seconds, then verify:
```bash
curl http://localhost:8015/api/document-text-extraction/health
```

**Expected**: `{"service":"document_text_extraction","status":"healthy",...}`

---

### **2. Test with Your PDF:**

```bash
# Make test script executable
chmod +x test-service1.sh

# Run test with your PDF
./test-service1.sh /path/to/your/document.pdf
```

**That's it!** The script will:
- ✅ Copy your PDF to Service 1
- ✅ Add it to the database
- ✅ Extract text automatically
- ✅ Show you the results

---

### **3. View Results:**

```bash
# See all extracted files
docker exec service1-api ls -lh /app/output/DOC_*/extracted_text/

# View first page
docker exec service1-api cat /app/output/DOC_*/extracted_text/page_0001_fitz.md
```

---

## 📋 **Manual Testing (Step-by-Step)**

If you prefer to do it manually, see `TESTING_GUIDE.md` for detailed instructions.

---

## 🔧 **What You Need**

- **Docker** and **Docker Compose** installed
- **A PDF file** to test with
- **That's it!** No Python, no PostgreSQL, nothing else needed.

---

## ✅ **Verification**

After running the test script, you should see:
- ✅ Status: 100 (complete)
- ✅ .md files created (one per page)
- ✅ Files in `/app/output/DOC_*/extracted_text/`

---

## 🆘 **Need Help?**

1. Check logs: `docker logs service1-api`
2. Check database: `docker exec postgres-service1-standalone psql -U postgres -d fcr001-text-extraction -c "\dt"`
3. See `TESTING_GUIDE.md` for detailed troubleshooting

---

**Happy Testing!** 🎉

