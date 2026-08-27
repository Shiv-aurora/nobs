FROM python:3.13-slim AS runtime

ARG INSTALL_GOOGLE=false
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONHASHSEED=random \
    PORT=8080
WORKDIR /app

COPY agent-service/pyproject.toml ./pyproject.toml
COPY agent-service/app ./app
COPY seed ./seed
RUN python -m pip install --no-cache-dir --upgrade pip && \
    if [ "$INSTALL_GOOGLE" = "true" ]; then \
      python -m pip install --no-cache-dir ".[google]"; \
    else \
      python -m pip install --no-cache-dir .; \
    fi

RUN addgroup --system --gid 65532 noping && \
    adduser --system --uid 65532 --ingroup noping --home /nonexistent --no-create-home noping
USER 65532:65532
EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8080/healthz', timeout=3)" || exit 1
CMD ["sh", "-c", "exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT} --workers 1 --proxy-headers --forwarded-allow-ips='*'"]
