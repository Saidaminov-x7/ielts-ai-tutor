FROM node:22-alpine AS frontend-build
WORKDIR /frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run typecheck && npm run build

FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
WORKDIR /app
COPY pyproject.toml README.md ./
COPY alembic.ini ./
COPY app ./app
COPY migrations ./migrations
COPY data ./data
COPY --from=frontend-build /frontend/dist ./frontend/dist
RUN pip install --no-cache-dir .
RUN useradd --create-home --uid 10001 appuser && mkdir -p /data && chown appuser:appuser /data
ENTRYPOINT ["python", "-m", "app.container_entrypoint"]
ENV DATABASE_URL=sqlite:////data/ielts.db
CMD ["python", "-m", "app.main"]
