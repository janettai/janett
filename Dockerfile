FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Install dependencies first (better layer caching).
COPY pyproject.toml README.md ./
COPY src ./src
RUN pip install --upgrade pip && pip install .

# Railway provides $PORT at runtime.
ENV PORT=8000
EXPOSE 8000

CMD ["sh", "-c", "uvicorn janett.api.app:app --host 0.0.0.0 --port ${PORT}"]
