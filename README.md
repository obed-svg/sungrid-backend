# sungrid-backend

Django/DRF backend for SUN-GRID Control.

## Local dev
```bash
cp .env.example .env
docker compose -f docker-compose.dev.yml up -d redis
python -m venv .venv && source .venv/bin/activate
pip install -e '.[dev]'
python manage.py migrate
python manage.py runserver
```

## Tests
```bash
pytest
```
