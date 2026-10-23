FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Run as an unprivileged user.
RUN useradd --create-home --uid 10001 appuser \
    && chown -R appuser /app
USER appuser

EXPOSE 8000

# Apply migrations, then start the server. Development overrides this command
# in docker-compose.yml to enable --reload.
# Behind a reverse proxy, set FORWARDED_ALLOW_IPS to the proxy's address so uvicorn
# takes the client IP from X-Forwarded-For (used by the rate limiter).
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000 --proxy-headers"]
