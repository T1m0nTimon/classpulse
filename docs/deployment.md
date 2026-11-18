# Deployment

ClassPulse is one small process (FastAPI serving the built React app) plus a database. Pick what fits your school.

## Which setup?

| Setup | Students reach it via | Effort | Cost |
|---|---|---|---|
| Teacher laptop | same Wi-Fi only (if devices may see each other) | lowest | free |
| Raspberry Pi in school | school network | low | ~60 € once |
| VPS with domain (recommended) | any network, incl. mobile data | medium | ~3–5 €/month |

A teacher can use ClassPulse from a laptop, PC or **iPad** in all setups — it's a web app.

## Laptop

```bash
scripts/install.sh   # or scripts\install.ps1 on Windows
scripts/start.sh     # or scripts\start.ps1
```

Open `http://localhost:8000`. The session page shows the laptop's network address if you opened it via `localhost`; switch to that address so the QR code works for phones. Allow port 8000 in the firewall when asked.

## Raspberry Pi (Pi 4/5, 64-bit OS)

Either the install script above (needs Python 3.11+ and Node.js 20+), or Docker:

```bash
curl -fsSL https://get.docker.com | sh
git clone https://github.com/<you>/classpulse && cd classpulse
cp .env.example .env && nano .env      # set SECRET_KEY
docker compose up -d app
```

Give the Pi a fixed IP in your router and set `PUBLIC_URL=http://<pi-ip>:8000`.

## VPS / Linux server with HTTPS

1. A server with Docker, a domain whose A/AAAA record points to it, ports 80 and 443 open.
2. `.env`:
   ```env
   SECRET_KEY=<long random>
   DOMAIN=classpulse.example.org
   PUBLIC_URL=https://classpulse.example.org
   SECURE_COOKIES=true
   POSTGRES_PASSWORD=<long random>
   DATABASE_URL=postgresql+psycopg://classpulse:<POSTGRES_PASSWORD>@db:5432/classpulse
   ```
3. `docker compose --profile prod up -d`

Caddy fetches certificates automatically. Migrations run on startup.

### Updates

```bash
git pull && docker compose --profile prod up -d --build
```

### Backups

```bash
docker compose exec db pg_dump -U classpulse classpulse > backup.sql
```

## Other reverse proxies (nginx, Traefik)

Forward HTTP **and WebSocket** traffic (`/ws/`) to port 8000 and set `X-Forwarded-For`/`X-Forwarded-Proto`. Disable or minimise access logs to protect student privacy. nginx example:

```nginx
location / {
    proxy_pass http://127.0.0.1:8000;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
    proxy_set_header Host $host;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
}
access_log off;
```

## Scaling

Run **one** worker process. Live updates and rate limits are kept in memory, which comfortably handles hundreds of concurrent students on a 1-CPU VPS. For multiple workers or servers, the hub in `backend/classpulse/realtime.py` and the limiter in `security.py` would need Redis.
