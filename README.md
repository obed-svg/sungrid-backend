# sungrid-backend

Django/DRF backend for SUN-GRID Control.

## Production Deployment

Production runs from the **SUN-GRID-control** monorepo root, not this directory.

### 1. Clone the monorepo
```bash
git clone <gitlab-url>/SUN-GRID-control.git
cd SUN-GRID-control
```

### 2. Place VPN config
```bash
cp /path/to/client.ovpn openvpn/client.ovpn
```

### 3. Configure environment
```bash
cp .env.example .env
nano .env
```

Required values to set:
- `DJANGO_SECRET_KEY` — 50+ char random string
- `DJANGO_ALLOWED_HOSTS` — server IP or domain
- `DJANGO_CSRF_TRUSTED_ORIGINS` — `https://YOUR_SERVER_IP`
- `RECLOSER_GATEWAY_IP` — recloser IP on VPN (e.g. `10.9.1.172`)

### 4. Generate TLS certificate
```bash
openssl req -x509 -newkey rsa:2048 -keyout certs/key.pem -out certs/cert.pem \
  -days 365 -nodes -subj "/CN=YOUR_SERVER_IP"
```

### 5. Start the stack
```bash
docker compose up -d --build
```

### 6. Run migrations
```bash
docker compose exec api python manage.py migrate
```

### 7. Create superuser
```bash
docker compose exec api python manage.py createsuperuser
```

Access at `https://YOUR_SERVER_IP:8443`.

---

## Local Dev
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
