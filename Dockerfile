# ---- build the frontend ----
FROM node:22-slim AS web
WORKDIR /web
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# ---- runtime (multi-arch: amd64, arm64 / Raspberry Pi 4/5) ----
FROM python:3.13-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 \
    DATABASE_URL=sqlite:////data/classpulse.db FRONTEND_DIST=../frontend/dist
WORKDIR /app/backend
COPY backend/pyproject.toml ./
COPY backend/classpulse ./classpulse
RUN pip install --no-cache-dir ".[postgres]"
COPY backend/alembic.ini ./
COPY backend/alembic ./alembic
COPY --from=web /web/dist /app/frontend/dist
RUN useradd --system --uid 1000 classpulse && mkdir /data && chown classpulse /data
USER classpulse
VOLUME /data
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=3s CMD python -c "import urllib.request;urllib.request.urlopen('http://127.0.0.1:8000/api/health')"
# Single worker on purpose: live updates are kept in process memory (see docs/deployment.md).
CMD ["uvicorn", "classpulse.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--forwarded-allow-ips", "*", "--no-access-log"]
