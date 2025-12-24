# Deploying to Render

This guide will walk you through deploying the AI Tutor backend and database to Render.

## Prerequisites

1. A Render account (sign up at https://render.com)
2. Your OpenAI API key
3. Your YouTube API key (optional, for video features)

## Step-by-Step Deployment

### Option 1: Using Render Dashboard (Recommended for first-time deployment)

#### 1. Create PostgreSQL Database

1. Go to [Render Dashboard](https://dashboard.render.com)
2. Click **"New +"** → **"PostgreSQL"**
3. Configure:
   - **Name**: `ai-tutor-db`
   - **Database**: `ai_tutor`
   - **User**: `ai_tutor_user`
   - **Region**: Choose closest to your users (e.g., `Oregon`)
   - **Plan**: Start with `Free` (upgrade later for production)
4. Click **"Create Database"**
5. **Important**: Copy the **Internal Database URL** (you'll need this)

#### 2. Create Web Service (Backend)

1. In Render Dashboard, click **"New +"** → **"Web Service"**
2. Connect your GitHub repository:
   - Select your repository
   - Choose the branch (usually `main` or `master`)
3. Configure the service:
   - **Name**: `ai-tutor-backend`
   - **Region**: Same as your database
   - **Branch**: `main` (or your default branch)
   - **Root Directory**: `backend`
   - **Environment**: `Python 3`
   - **Build Command**: 
     ```bash
     pip install -r requirements.txt && alembic upgrade head
     ```
   - **Start Command**:
     ```bash
     uvicorn app.main:app --host 0.0.0.0 --port $PORT
     ```
4. Add Environment Variables (click **"Advanced"** → **"Add Environment Variable"**):
   
   **Required:**
   ```
   DATABASE_URL=<Internal Database URL from step 1>
   OPENAI_API_KEY=<your-openai-api-key>
   SECRET_KEY=<generate-a-random-secret-key>
   YOUTUBE_API_KEY=<your-youtube-api-key>
   ```
   
   **Optional (with defaults):**
   ```
   ALGORITHM=HS256
   ACCESS_TOKEN_EXPIRE_MINUTES=30
   ENVIRONMENT=production
   CORS_ORIGINS=https://your-frontend.vercel.app,http://localhost:3000
   MAX_UPLOAD_SIZE=5242880
   UPLOAD_DIR=uploads
   RATE_LIMIT_PER_MINUTE=20
   ```
5. Click **"Create Web Service"**

#### 3. Generate SECRET_KEY

You can generate a secure secret key using Python:
```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

Or use an online generator: https://randomkeygen.com/

### Option 2: Using render.yaml (Blueprint)

1. Push `render.yaml` to your repository root
2. Go to Render Dashboard → **"New +"** → **"Blueprint"**
3. Connect your repository
4. Render will automatically detect and create services from `render.yaml`
5. You'll still need to manually set:
   - `OPENAI_API_KEY`
   - `YOUTUBE_API_KEY`
   - Update `CORS_ORIGINS` with your frontend URL

## Post-Deployment Steps

### 1. Update CORS Origins

After deploying, update `CORS_ORIGINS` in Render dashboard to include your frontend URL:
```
CORS_ORIGINS=https://your-app.vercel.app,http://localhost:3000
```

### 2. Test the Deployment

1. Visit your backend URL: `https://ai-tutor-backend.onrender.com` (or your custom domain)
2. Check health endpoint: `https://ai-tutor-backend.onrender.com/api/health`
3. View API docs: `https://ai-tutor-backend.onrender.com/docs`

### 3. Update Frontend Environment Variables

Update your frontend `.env.local` or Vercel environment variables:
```env
NEXT_PUBLIC_API_URL=https://ai-tutor-backend.onrender.com
```

## Database Migrations

Render will automatically run migrations during build (`alembic upgrade head`).

To manually run migrations:
1. Go to your web service in Render
2. Click **"Shell"** tab
3. Run:
   ```bash
   alembic upgrade head
   ```

## Troubleshooting

### Database Connection Issues

- Ensure `DATABASE_URL` uses the **Internal Database URL** (not external)
- Check that database and web service are in the same region
- Verify database is not paused (free tier pauses after inactivity)

### Build Failures

- Check build logs in Render dashboard
- Ensure all dependencies are in `requirements.txt`
- Verify Python version compatibility

### CORS Errors

- Update `CORS_ORIGINS` to include your frontend domain
- Ensure no trailing slashes in URLs
- Check that frontend is using correct API URL

### Service Pauses (Free Tier)

- Free tier services pause after 15 minutes of inactivity
- First request after pause takes ~30 seconds to wake up
- Consider upgrading to paid plan for production

## Upgrading for Production

1. **Database**: Upgrade to `Starter` plan ($7/month) for:
   - No automatic pauses
   - Better performance
   - Automated backups

2. **Web Service**: Upgrade to `Starter` plan ($7/month) for:
   - No automatic pauses
   - Better performance
   - Custom domains

## Environment Variables Reference

| Variable | Required | Description | Example |
|----------|----------|-------------|---------|
| `DATABASE_URL` | Yes | PostgreSQL connection string | `postgresql://user:pass@host/db` |
| `OPENAI_API_KEY` | Yes | OpenAI API key | `sk-...` |
| `SECRET_KEY` | Yes | JWT secret key | Random 32+ character string |
| `YOUTUBE_API_KEY` | No | YouTube Data API key | `AIza...` |
| `CORS_ORIGINS` | Yes | Allowed frontend origins | `https://app.com,http://localhost:3000` |
| `ENVIRONMENT` | No | Environment name | `production` |
| `ALGORITHM` | No | JWT algorithm | `HS256` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | No | Token expiry | `30` |

## Monitoring

- View logs: Render Dashboard → Your Service → **"Logs"** tab
- Monitor metrics: Render Dashboard → Your Service → **"Metrics"** tab
- Set up alerts: Render Dashboard → Your Service → **"Alerts"**

## Support

- Render Docs: https://render.com/docs
- Render Community: https://community.render.com

