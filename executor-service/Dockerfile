FROM python:3.13-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PORT=8080
WORKDIR /app
COPY executor-service/pyproject.toml ./pyproject.toml
RUN python -m pip install --no-cache-dir --upgrade pip && \
    mkdir -p app && touch app/__init__.py && python -m pip install --no-cache-dir . && rm -rf app
COPY executor-service/app ./app
RUN addgroup --system --gid 65532 nobs && \
    adduser --system --uid 65532 --ingroup nobs --home /nonexistent --no-create-home nobs
USER 65532:65532
EXPOSE 8080
CMD ["sh", "-c", "exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT} --workers 1 --proxy-headers --forwarded-allow-ips='*'"]
