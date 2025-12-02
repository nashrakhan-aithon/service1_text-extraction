# S3 Integration - Requirements Checklist

This document lists everything you need to provide/prepare on your side before implementing S3 integration.

---

## ✅ Required Information from You

### 1. AWS Account & Access
- [ ] **AWS Account** - Do you have an AWS account?
- [ ] **AWS Access Method** - How will the application access S3?
  - Option A: AWS Access Key ID + Secret Access Key (for local/dev)
  - Option B: IAM Role (for EC2/ECS/Lambda - recommended for production)
  - Option C: Environment variables already set up

### 2. S3 Bucket Details
- [ ] **Bucket Name** - What is your S3 bucket name?
  - Example: `my-document-extraction-bucket`
  - Must be globally unique across all AWS accounts
  - Must follow S3 naming rules (lowercase, no spaces, etc.)

- [ ] **AWS Region** - Which AWS region is your bucket in?
  - Examples: `us-east-1`, `us-west-2`, `eu-west-1`, `ap-south-1`
  - Default: `us-east-1` (if not specified)

- [ ] **Bucket Location** - Does the bucket already exist?
  - [ ] Yes, bucket exists
  - [ ] No, needs to be created
  - [ ] Not sure

### 3. AWS Credentials (Choose One Method)

#### Method A: Access Key ID + Secret Access Key
- [ ] **AWS Access Key ID** - Your AWS access key
- [ ] **AWS Secret Access Key** - Your AWS secret key
- ⚠️ **Security Note:** These will be stored in `.envvar-service1` file
- ⚠️ **Best Practice:** Create a dedicated IAM user with minimal permissions (see below)

#### Method B: IAM Role (Recommended for Production)
- [ ] **IAM Role ARN** - If using IAM role (for EC2/ECS/Lambda)
- [ ] **Role is attached** - IAM role is already attached to your compute resource
- ✅ **Security Note:** No credentials needed in config file - uses role automatically

#### Method C: Environment Variables
- [ ] **AWS_ACCESS_KEY_ID** - Already set as environment variable
- [ ] **AWS_SECRET_ACCESS_KEY** - Already set as environment variable
- ✅ **Security Note:** No credentials needed in config file

### 4. S3 Folder/Path Structure
- [ ] **S3 Prefix/Folder** - Do you want files in a specific folder?
  - Example: `service1-extracted-text` → Files will be at `s3://bucket/service1-extracted-text/doc_id/...`
  - Example: `documents/extracted` → Files will be at `s3://bucket/documents/extracted/doc_id/...`
  - Leave empty if you want files directly in bucket root
  - **Default:** None (files go directly under bucket)

### 5. Permissions & Security
- [ ] **IAM Policy** - Do you have IAM policy/permissions set up?
  - Required permissions:
    - `s3:PutObject` - To upload files
    - `s3:GetObject` - To read files (optional, for verification)
    - `s3:ListBucket` - To list files (optional, for debugging)
    - `s3:HeadObject` - To check if file exists (optional)

- [ ] **Bucket Policy** - Any bucket-level policies?
- [ ] **Encryption** - Do you need encryption?
  - SSE-S3 (default, free)
  - SSE-KMS (requires KMS key)
  - SSE-C (customer-provided keys)

---

## 📋 Information to Provide

Please fill out this template and provide it:

```
S3 Configuration Details:
========================

1. Bucket Name: _______________________
   (e.g., my-doc-extraction-bucket)

2. AWS Region: _______________________
   (e.g., us-east-1)

3. Access Method: [ ] Access Keys  [ ] IAM Role  [ ] Environment Variables

4. If using Access Keys:
   - Access Key ID: _______________________
   - Secret Access Key: _______________________
   (⚠️ Keep these secure - will be stored in .envvar-service1)

5. S3 Prefix/Folder (optional): _______________________
   (e.g., service1-extracted-text or leave blank)

6. Bucket Status: [ ] Exists  [ ] Needs to be created  [ ] Not sure
```

---

## 🔧 What I'll Need You to Do

### Step 1: Create S3 Bucket (if it doesn't exist)
If you don't have a bucket yet, you can create one via:
- AWS Console: https://console.aws.amazon.com/s3/
- AWS CLI: `aws s3 mb s3://your-bucket-name --region us-east-1`
- Or I can provide instructions

### Step 2: Set Up IAM User/Role (if using Access Keys)
1. Create IAM user in AWS Console
2. Attach policy with S3 permissions (see below)
3. Create Access Key for the user
4. Save Access Key ID and Secret Access Key securely

**Required IAM Policy:**
```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "s3:PutObject",
                "s3:GetObject",
                "s3:ListBucket",
                "s3:HeadObject"
            ],
            "Resource": [
                "arn:aws:s3:::your-bucket-name",
                "arn:aws:s3:::your-bucket-name/*"
            ]
        }
    ]
}
```

### Step 3: Test Access (Optional but Recommended)
Test that you can access the bucket:
```bash
# Using AWS CLI
aws s3 ls s3://your-bucket-name/

# Or test upload
echo "test" > test.txt
aws s3 cp test.txt s3://your-bucket-name/test.txt
aws s3 rm s3://your-bucket-name/test.txt
```

---

## 🚫 What You DON'T Need to Provide

- ❌ Code changes (I'll handle that)
- ❌ Implementation details (I'll implement)
- ❌ Testing scripts (I can create them)
- ❌ Documentation (already created)

---

## ⚠️ Security Checklist

Before providing credentials, ensure:

- [ ] IAM user/role follows **principle of least privilege** (only S3 permissions needed)
- [ ] Access keys are **not shared** via insecure channels (email, chat, etc.)
- [ ] `.envvar-service1` file is in `.gitignore` (won't be committed to git)
- [ ] For production: Use IAM roles instead of access keys
- [ ] Consider using AWS Secrets Manager for credentials (advanced)

---

## 📝 Quick Start - Minimum Requirements

If you want to get started quickly, I need at minimum:

1. **Bucket Name** - The S3 bucket where files will be stored
2. **AWS Region** - Where the bucket is located
3. **Access Method** - How to authenticate (keys, role, or env vars)

Everything else can use defaults or be configured later.

---

## ❓ Questions to Answer

Please answer these questions:

1. **Do you already have an S3 bucket?**
   - Yes → Provide bucket name and region
   - No → I can provide instructions to create one

2. **How will the application run?**
   - Local development → Use Access Keys
   - Docker container → Use Access Keys or IAM role
   - EC2/ECS → Use IAM role (recommended)
   - Lambda → Use IAM role

3. **Do you have AWS credentials already?**
   - Yes → Provide Access Key ID and Secret (or confirm IAM role)
   - No → I can provide instructions to create them

4. **Any specific folder structure in S3?**
   - Yes → Provide the prefix/folder path
   - No → Files will go directly under bucket

5. **Any security/compliance requirements?**
   - Encryption requirements?
   - Access restrictions?
   - Audit logging needs?

---

## 🎯 Next Steps

Once you provide the information above, I will:

1. ✅ Add boto3 to requirements.txt
2. ✅ Create S3 service class
3. ✅ Update configuration to use your S3 details
4. ✅ Modify the save method to upload to S3
5. ✅ Update database to store S3 URIs
6. ✅ Add error handling and logging
7. ✅ Test the integration

**Ready to proceed?** Just provide the S3 configuration details from the template above!

