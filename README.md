# VOD Scraper — Interview Task (Postgres edition)

This repository is configured to use PostgreSQL by default (see `vod_project/vod_project/settings.py`).

## Quick start with PostgreSQL (recommended, uses Docker Compose)

1. Start Postgres and Redis (background):
```bash
docker compose up -d db redis
```

2. Create a Python virtualenv and install dependencies locally (optional for running management commands from host):
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

3. Run migrations using the same DATABASE_URL as docker-compose (the settings read DATABASE_URL automatically):
```bash
export DATABASE_URL=postgres://voduser:vodpass@localhost:5432/vod
python api/manage.py migrate
python api/manage.py createsuperuser  # optional
```

4. Run the development server:
```bash
export DATABASE_URL=postgres://voduser:vodpass@localhost:5432/vod
python api/manage.py runserver 0.0.0.0:8000
```

---
