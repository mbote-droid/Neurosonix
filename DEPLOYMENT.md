# NeuroSonix Deployment Guide

Complete guide to deploy NeuroSonix as a production SaaS application.

## Prerequisites

- Docker & Docker Compose (for containerized deployment)
- Git (for version control)
- Node.js 18+ (for frontend development)
- Python 3.11+ (for backend development)
- GitHub account (for Actions CI/CD)
- Vercel account (for frontend hosting) — Optional
- Render.com account (for backend hosting) — Optional

---

## **Option 1: Local Docker Development** (Recommended for testing)

### 1. Clone the repository
```bash
git clone https://github.com/mbote-droid/neurosonix.git
cd neurosonix
```

### 2. Create environment file
```bash
cp backend/.env.example backend/.env
# Edit backend/.env as needed
```

### 3. Run with Docker Compose
```bash
docker-compose up --build
```

Services will be available at:
- **Frontend:** http://localhost:3000
- **Backend API:** http://localhost:8000
- **API Docs:** http://localhost:8000/docs

### 4. Verify services are healthy
```bash
# Check status
docker-compose ps

# View logs
docker-compose logs -f

# Test backend health
curl http://localhost:8000/health
```

### 5. Stop services
```bash
docker-compose down
```

---

## **Option 2: Deploy Frontend to Vercel** (Free tier available)

### 1. Prepare frontend
```bash
cd frontend
npm install
npm run build  # Verify build works locally
```

### 2. Connect to Vercel
```bash
npm install -g vercel
vercel login  # Sign in with GitHub
vercel        # Deploy (follow prompts)
```

### 3. Environment variables
In Vercel dashboard, set:
```
VITE_API_URL=https://your-backend-url
```

### 4. Auto-deploy on push
Vercel auto-deploys from the main branch. No additional setup needed.

---

## **Option 3: Deploy Backend to Render.com** (Free tier available)

### 1. Connect GitHub repository
- Go to render.com
- Click "New +" → "Web Service"
- Connect your GitHub account
- Select `neurosonix` repository

### 2. Configure service
- **Name:** neurosonix-backend
- **Environment:** Python 3.11
- **Build command:** `pip install -r backend/requirements.txt`
- **Start command:** `cd backend && python main.py`
- **Port:** 8000

### 3. Set environment variables
In Render dashboard → Environment:
```
ENV=production
PYTHONUNBUFFERED=1
```

### Agentic evaluation (LLM) variables

The evaluation swarm runs **offline by default** — no configuration required.
To enable live LLM scoring, set:

```
NEUROSONIX_LLM_PROVIDER=anthropic   # or "none" to force offline
NEUROSONIX_LLM_MODEL=claude-opus-4-8
ANTHROPIC_API_KEY=sk-ant-...         # required only for live scoring
```

Without `ANTHROPIC_API_KEY`, the platform serves deterministic heuristic
scores and every result is flagged `degraded` — the app stays fully functional.

### 4. Deploy
Push to `main` branch — Render auto-deploys.

### 5. Get your backend URL
```
https://neurosonix-backend.onrender.com
```

Update frontend's `VITE_API_URL` to this URL in Vercel.

---

## **Option 4: Deploy on Your Own Server** (AWS, DigitalOcean, etc.)

### 1. SSH into server
```bash
ssh user@your-server-ip
```

### 2. Install Docker
```bash
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER
newgrp docker
```

### 3. Clone repository
```bash
git clone https://github.com/mbote-droid/neurosonix.git
cd neurosonix
```

### 4. Create .env file
```bash
cp backend/.env.example backend/.env
# Edit with your server's IP/domain
```

### 5. Run with Docker Compose
```bash
docker-compose up -d
```

### 6. Set up reverse proxy (Nginx)
```bash
# Install Nginx
sudo apt-get install nginx

# Create config
sudo nano /etc/nginx/sites-available/neurosonix
```

Add:
```nginx
server {
    server_name your-domain.com;
    
    location / {
        proxy_pass http://localhost:3000;
        proxy_set_header Host $host;
    }
    
    location /api/ {
        proxy_pass http://localhost:8000;
    }
}
```

Enable:
```bash
sudo ln -s /etc/nginx/sites-available/neurosonix /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

### 7. Set up SSL (Let's Encrypt)
```bash
sudo apt-get install certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain.com
```

---

## **CI/CD Pipeline** (GitHub Actions)

The repository includes automated CI/CD:

1. **On every push to `main`:**
   - ✅ Backend tests run (pytest)
   - ✅ Backend linting (black, flake8)
   - ✅ Frontend build verification
   - ✅ Docker images build
   - ✅ Code quality checks

2. **View results:**
   Go to GitHub → Actions tab to see pipeline results.

3. **Deploy automatically:**
   - Vercel deploys frontend on every push
   - Render deploys backend on every push

---

## **Environment Variables**

### Backend (.env)
```env
# Flask/FastAPI
ENV=production
DEBUG=false
LOG_LEVEL=INFO

# CORS
CORS_ORIGINS=["https://your-frontend.com"]

# Audio processing
SAMPLE_RATE=16000
WHISPER_MODEL=base
WHISPER_DEVICE=cpu

# Database
DATABASE_URL=sqlite:///neurosonix.db
```

### Frontend (.env.local in Vercel)
```env
VITE_API_URL=https://your-backend-url
```

---

## **Monitoring & Logging**

### View backend logs (Docker)
```bash
docker-compose logs -f backend
```

### View frontend logs (Docker)
```bash
docker-compose logs -f frontend
```

### Health checks
```bash
# Backend health
curl https://your-backend-url/health

# Frontend availability
curl https://your-frontend-url
```

### Check container status
```bash
docker-compose ps
docker stats
```

---

## **Scaling Considerations**

### For larger workloads:
1. **Use PostgreSQL** instead of SQLite
2. **Add Redis** for caching
3. **Use a task queue** (Celery) for long-running audio processing
4. **Add load balancing** (Nginx) for multiple backend instances
5. **Use CDN** (Cloudflare) for frontend assets

---

## **Security Checklist**

- [ ] Update `.env` with secure secrets
- [ ] Enable HTTPS/SSL (Let's Encrypt)
- [ ] Set CORS properly in backend
- [ ] Use strong database passwords
- [ ] Enable rate limiting on API
- [ ] Set up firewall rules
- [ ] Rotate logs regularly
- [ ] Monitor for vulnerabilities (Dependabot)
- [ ] Back up database regularly

---

## **Troubleshooting**

### Backend won't start
```bash
docker-compose logs backend
# Check for Python errors, missing dependencies
```

### CORS errors
Update `CORS_ORIGINS` in backend .env to match your frontend URL.

### Audio processing slow
- Check system resources: `docker stats`
- Consider using a more powerful CPU
- Enable GPU if available: `WHISPER_DEVICE=cuda`

### Database errors
```bash
# Reset database (WARNING: loses data)
rm backend/neurosonix.db
docker-compose restart backend
```

---

## **Support**

- **Issues:** https://github.com/mbote-droid/neurosonix/issues
- **Discussions:** https://github.com/mbote-droid/neurosonix/discussions

---

**Last updated:** 2026-07-15
