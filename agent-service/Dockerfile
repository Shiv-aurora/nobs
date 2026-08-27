FROM python:3.13-slim AS runtime
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PORT=8080
WORKDIR /app
COPY pyproject.toml ./
COPY app ./app
COPY ../seed ./seed
RUN pip install --no-cache-dir .
USER 65532:65532
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT}"]
