# Backend Setup and Testing Guide

This guide will walk you through setting up and testing the AI Tutor backend.

## Prerequisites

1. **Python 3.9+** installed
2. **PostgreSQL** installed and running
3. **OpenAI API Key** (get from https://platform.openai.com/api-keys)

---

## Step 1: PostgreSQL Setup

### Install PostgreSQL (if not installed)

**macOS:**
```bash
brew install postgresql@15
brew services start postgresql@15
```

**Ubuntu/Debian:**
```bash
sudo apt update
sudo apt install postgresql postgresql-contrib
sudo systemctl start postgresql
```

**Windows:**
Download from https://www.postgresql.org/download/windows/

### Create Database

```bash
# Connect to PostgreSQL
psql postgres

# Inside psql, run:
CREATE DATABASE ai_tutor_db;
CREATE USER ai_tutor_user WITH PASSWORD 'your_secure_password';
GRANT ALL PRIVILEGES ON DATABASE ai_tutor_db TO ai_tutor_user;
\q
```

---

## Step 2: Backend Environment Setup

### 1. Navigate to backend directory
```bash
cd /Users/ikehi/Downloads/ai_tutor/backend
```

### 2. Create virtual environment
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install dependencies
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

This will install:
- FastAPI, Uvicorn
- SQLAlchemy, PostgreSQL driver
- OpenAI SDK
- EasyOCR (this may take a few minutes)
- JWT authentication libraries
- And more...

### 4. Create .env file
```bash
cp env.example .env
```

### 5. Edit .env file
Open `.env` and configure:

```env
# Database - IMPORTANT: Update with your actual credentials
DATABASE_URL=postgresql://ai_tutor_user:your_secure_password@localhost:5432/ai_tutor_db

# OpenAI API - IMPORTANT: Add your actual API key
OPENAI_API_KEY=sk-proj-xxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# JWT Secret - Generate a secure key
SECRET_KEY=your_generated_secret_key_here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Environment
ENVIRONMENT=development

# CORS (for frontend)
CORS_ORIGINS=http://localhost:3000,http://localhost:8000

# File Upload
MAX_UPLOAD_SIZE=5242880
UPLOAD_DIR=uploads

# Rate Limiting
RATE_LIMIT_PER_MINUTE=20
```

**Generate a secure SECRET_KEY:**
```bash
openssl rand -hex 32
```

Copy the output and paste it as your SECRET_KEY in `.env`

---

## Step 3: Database Migrations

### 1. Create initial migration
```bash
alembic revision --autogenerate -m "Initial database setup"
```

### 2. Apply migration
```bash
alembic upgrade head
```

This will create all the database tables:
- `users`
- `user_subjects`
- `question_history`
- `study_plans`
- `exam_attempts`

### Verify tables created
```bash
psql ai_tutor_db

# Inside psql:
\dt

# You should see all 5 tables listed
\q
```

---

## Step 4: Run the Backend

### Start the server
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

You should see:
```
INFO:     Uvicorn running on http://0.0.0.0:8000
INFO:     Application startup complete.
```

### Access API Documentation
Open your browser and go to:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **Health Check**: http://localhost:8000/

---

## Step 5: Testing the API

### Option 1: Using Swagger UI (Easiest)

1. Go to http://localhost:8000/docs
2. You'll see all API endpoints organized by category

**Test Flow:**

**A. Register a User**
1. Find `POST /api/auth/register`
2. Click "Try it out"
3. Use this test data:
```json
{
  "email": "student@test.com",
  "phone": "08012345678",
  "password": "password123",
  "full_name": "Test Student",
  "role": "student",
  "student_class": "SS3",
  "subjects": ["Mathematics", "Physics", "English Language"]
}
```
4. Click "Execute"
5. You should get a **201 response** with an access token

**B. Login**
1. Find `POST /api/auth/login`
2. Try it out with:
```json
{
  "email": "student@test.com",
  "password": "password123"
}
```
3. Copy the `access_token` from response

**C. Authorize (Important!)**
1. Click the **"Authorize"** button at the top right
2. Paste: `Bearer your_access_token_here`
3. Click "Authorize"

**D. Test Question Solving**
1. Find `POST /api/questions/solve`
2. Try it out:
```json
{
  "question_text": "Simplify: 3x + 5x - 2x",
  "subject": "Mathematics"
}
```
3. You should get a step-by-step AI solution!

**E. Test Topic Teaching**
1. Find `POST /api/topics/teach`
2. Try:
```json
{
  "subject": "Mathematics",
  "topic": "Quadratic Equations",
  "difficulty_level": "medium"
}
```

**F. Create Study Plan**
1. Find `POST /api/study-plans/generate`
2. Try:
```json
{
  "target_exam": "WAEC",
  "hours_per_day": 3,
  "days_per_week": 5,
  "subjects": ["Mathematics", "Physics"],
  "weak_areas": ["Calculus"]
}
```

**G. Create Mock Exam**
1. Find `POST /api/exams/create`
2. Try:
```json
{
  "exam_type": "WAEC",
  "subject": "Mathematics",
  "number_of_questions": 3,
  "time_limit_minutes": 10
}
```

**H. Get Dashboard**
1. Find `GET /api/dashboard/student/overview`
2. Execute to see your progress

### Option 2: Using cURL (Command Line)

```bash
# Register
curl -X POST "http://localhost:8000/api/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "student@test.com",
    "password": "password123",
    "full_name": "Test Student",
    "role": "student",
    "student_class": "SS3",
    "subjects": ["Mathematics"]
  }'

# Login and get token
TOKEN=$(curl -X POST "http://localhost:8000/api/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"email": "student@test.com", "password": "password123"}' \
  | jq -r '.access_token')

echo "Token: $TOKEN"

# Get profile
curl -X GET "http://localhost:8000/api/auth/me" \
  -H "Authorization: Bearer $TOKEN"

# Solve question
curl -X POST "http://localhost:8000/api/questions/solve" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "question_text": "What is 2 + 2?",
    "subject": "Mathematics"
  }'
```

---

## Step 6: Test OCR (Image Upload)

### Using Swagger UI:

1. Find `POST /api/questions/solve-with-image`
2. Click "Try it out"
3. Click "Choose File" and upload an image with a math problem
4. Add subject (optional): "Mathematics"
5. Click "Execute"
6. The OCR will extract text and AI will solve it!

### Test Image Requirements:
- Clear, high-resolution image
- Good lighting
- Text should be clearly visible
- Supported formats: JPG, PNG, GIF

---

## Troubleshooting

### Issue: "Could not connect to database"
**Solution:**
- Check PostgreSQL is running: `brew services list` (macOS) or `sudo systemctl status postgresql` (Linux)
- Verify DATABASE_URL in `.env` is correct
- Test connection: `psql ai_tutor_db`

### Issue: "OpenAI API error"
**Solution:**
- Verify your OPENAI_API_KEY in `.env`
- Check you have credits in your OpenAI account
- Test key: https://platform.openai.com/api-keys

### Issue: "Module not found"
**Solution:**
- Make sure virtual environment is activated
- Reinstall: `pip install -r requirements.txt`

### Issue: "EasyOCR download error"
**Solution:**
- EasyOCR downloads models on first use
- Requires ~500MB download
- Make sure you have internet connection

### Issue: "Alembic can't find models"
**Solution:**
- Make sure all models are imported in `alembic/env.py`
- Run: `alembic revision --autogenerate -m "message"`

---

## Performance Notes

### First OCR Request:
- EasyOCR downloads language models (~500MB) on first use
- Subsequent requests will be much faster
- Models are cached locally

### OpenAI API:
- GPT-4o-mini is cost-effective: ~$0.15 per 1M input tokens
- Average question costs < $0.01
- Responses typically take 2-5 seconds

---

## What to Check

✅ **Database**
- [ ] PostgreSQL is running
- [ ] Database `ai_tutor_db` exists
- [ ] All 5 tables created
- [ ] Can register and login users

✅ **AI Features**
- [ ] Question solving works
- [ ] Topic teaching works
- [ ] Study plan generation works
- [ ] Mock exam creation works

✅ **OCR**
- [ ] Image upload works
- [ ] Text extraction works
- [ ] Can solve questions from images

✅ **Authentication**
- [ ] Registration works
- [ ] Login returns JWT token
- [ ] Protected endpoints require token
- [ ] Can get user profile

✅ **Dashboard**
- [ ] Student dashboard shows stats
- [ ] Progress tracking works
- [ ] Exam history displays

---

## Next Steps After Testing

1. ✅ Confirm all endpoints work
2. ✅ Test with real WAEC/JAMB questions
3. ✅ Verify AI responses are accurate
4. ✅ Check OCR accuracy with sample images
5. → Move to Frontend development

---

## Need Help?

If you encounter issues:
1. Check the terminal for error messages
2. Check PostgreSQL logs
3. Verify all environment variables are set
4. Make sure virtual environment is activated

## Report Your Test Results

Please let me know:
- ✅ Which endpoints work
- ❌ Which endpoints have issues
- 📊 Overall impression of AI quality
- 🐛 Any bugs found


