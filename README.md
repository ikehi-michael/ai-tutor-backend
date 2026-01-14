# The Stem Studio Backend (FastAPI)

Backend API for The Stem Studio - AI-powered WAEC, NECO & JAMB exam preparation platform.

## Tech Stack

- **Framework**: FastAPI 0.109.0
- **Database**: PostgreSQL with SQLAlchemy ORM
- **AI/ML**: OpenAI GPT-4o-mini with Vision capabilities
- **Image Analysis**: GPT-4o-mini Vision (no OCR - better accuracy with equations & diagrams)
- **Authentication**: JWT (JSON Web Tokens)
- **Deployment**: Render

## Features

- ✅ User authentication (students, parents, admins)
- ✅ AI-powered question solving with step-by-step explanations
- ✅ Vision-based image analysis (equations, diagrams, handwriting)
- ✅ Topic-by-topic teaching
- ✅ Personalized study plan generation
- ✅ Mock exam creation and grading
- ✅ Progress tracking and analytics
- ✅ Parent dashboard

## Project Structure

```
backend/
├── app/
│   ├── api/
│   │   └── routes/          # API endpoints
│   │       ├── auth.py      # Authentication
│   │       ├── questions.py # Question solving
│   │       ├── topics.py    # Topic teaching
│   │       ├── exams.py     # Mock exams
│   │       ├── study_plans.py
│   │       └── dashboard.py
│   ├── core/                # Core configuration
│   │   ├── config.py        # Settings
│   │   ├── database.py      # DB connection
│   │   └── security.py      # Auth utilities
│   ├── models/              # Database models
│   │   ├── user.py
│   │   └── question.py
│   ├── schemas/             # Pydantic schemas
│   │   ├── user.py
│   │   └── question.py
│   ├── services/            # Business logic
│   │   └── ai_service.py    # OpenAI integration (text + vision)
│   └── main.py              # Application entry point
├── requirements.txt
└── README.md
```

## Setup Instructions

### 1. Create Virtual Environment

```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Set Up Environment Variables

Create a `.env` file in the backend directory:

```bash
cp env.example .env
```

Edit `.env` and add your actual values:

```env
DATABASE_URL=postgresql://username:password@localhost:5432/ai_tutor_db
OPENAI_API_KEY=your_openai_api_key_here
SECRET_KEY=your_secret_key_here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
ENVIRONMENT=development
CORS_ORIGINS=http://localhost:3000
```

To generate a secure SECRET_KEY:
```bash
openssl rand -hex 32
```

### 4. Set Up Database

Create PostgreSQL database:

```bash
createdb ai_tutor_db
```

Run migrations:

```bash
# Install alembic if not already installed
pip install alembic

# Create migration
alembic revision --autogenerate -m "Initial database setup"

# Apply migration
alembic upgrade head
```

### 5. Run the Server

Development mode:
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at: `http://localhost:8000`

API documentation: `http://localhost:8000/docs`

## API Endpoints

### Authentication
- `POST /api/auth/register` - Register new user
- `POST /api/auth/login` - Login
- `GET /api/auth/me` - Get current user profile
- `PUT /api/auth/me` - Update profile

### Questions
- `POST /api/questions/solve` - Solve a question (text or image)
- `POST /api/questions/solve-with-image` - Upload image and solve
- `GET /api/questions/history` - Get question history

### Topics
- `GET /api/topics/subjects` - List all subjects
- `POST /api/topics/teach` - Get AI explanation for a topic
- `POST /api/topics/simplify` - Simplify explanation
- `GET /api/topics/syllabus/{subject}` - Get syllabus for subject

### Study Plans
- `POST /api/study-plans/generate` - Generate personalized study plan
- `GET /api/study-plans/my-plans` - Get all user's study plans
- `GET /api/study-plans/active` - Get active study plan

### Exams
- `POST /api/exams/create` - Create mock exam
- `POST /api/exams/submit` - Submit exam answers
- `GET /api/exams/history` - Get exam history

### Dashboard
- `GET /api/dashboard/student/overview` - Student dashboard
- `GET /api/dashboard/student/progress-chart` - Progress chart data
- `GET /api/dashboard/parent/children` - Parent dashboard
- `GET /api/dashboard/parent/child/{id}/detailed` - Detailed child report

## Deployment to Render

1. Create account on [Render.com](https://render.com)
2. Create a new Web Service
3. Connect your GitHub repository
4. Configure:
   - **Environment**: Python 3
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
5. Add environment variables in Render dashboard
6. Deploy!

## Testing

Run tests:
```bash
pytest
```

## Notes for Data Scientists

- **AI Service** (`app/services/ai_service.py`): Contains all AI/ML logic using OpenAI
- **OCR Service** (`app/services/ocr_service.py`): EasyOCR implementation for image processing
- **Models** (`app/models/`): SQLAlchemy database models
- **Schemas** (`app/schemas/`): Pydantic models for request/response validation

The AI service can be extended with:
- Custom fine-tuned models
- Local LLMs (LLaMA, Mistral)
- Advanced prompt engineering
- Embeddings for question similarity
- Weakness detection algorithms


