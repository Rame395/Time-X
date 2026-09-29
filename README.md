# TIME-X — Production-ready full-stack watch store

FastAPI + PostgreSQL + responsive static frontend, packaged for production with Docker Compose and Caddy HTTPS.

## Local development

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload
```

\## Application Links



\### Customer



\[Customer Login](http://127.0.0.1:8000/account.html)



\### Admin



\[Admin Login](http://127.0.0.1:8000/admin/login.html)



\[Admin Dashboard](http://127.0.0.1:8000/admin/dashboard.html)



\### Local Development





