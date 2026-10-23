# Site Report API

FastAPI + SQLAlchemy (async) + PostgreSQL. Used by the mobile app and the admin panel.

## Setup

```bash
cp .env.example .env          # then fill in the values
docker compose -f ../docker-compose.yml up --build   # local dev (hot reload)
```

Production: `docker compose -f docker-compose.prod.yml up -d` with `POSTGRES_PASSWORD` set.
The container runs `alembic upgrade head` before starting the server.

Manual:

```bash
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload
```

## Configuration notes

- **`APPLE_ROOT_CA_PATH`**: StoreKit transactions are verified against Apple's root certificate.
  Download "Apple Root CA - G3" from Apple, convert it to PEM, and point this setting at it.
  Until it is set, every Apple purchase is rejected (fail closed).
- **`FORWARDED_ALLOW_IPS`**: set to your reverse proxy's address when the API runs behind one,
  so rate limits see the real client IP.
- **`CORS_ORIGINS`**: only these origins may call the API from a browser.

## Security model

- Access tokens are short-lived JWTs (`typ: access`). Refresh tokens are random, stored hashed,
  rotated on every use, and revoked for the whole user if a used token is presented again.
- Deactivated accounts lose access immediately (every request checks `is_active`).
- Login endpoints are rate limited. The limiter is in memory, so run one worker or move the
  store to Redis before scaling out.
- Self-service account deletion removes personal data and reports; payment records are kept
  (anonymised account row) for accounting.
- Stripe webhooks are signature-checked. Apple JWS tokens and notifications are verified
  against Apple's certificate chain.

## Migrations

`e1a2c3d4f5b6_security_and_integrity_fixes` adds `reports.client_id` (with a per-user unique
constraint), several indexes, and hashes existing refresh tokens in place, so current sessions
keep working. Run it against a copy of production data first.

Note: older migrations `d6aee6d034dc` and `8b5a53c0564b` add `NOT NULL` columns without defaults.
They work on an empty database but fail on a populated one; they are kept as-is because they have
already run wherever they matter.

## Tests

```bash
pip install -r requirements.txt
pytest
```

The suite runs against a temporary SQLite database. It covers the auth, OTP, refresh, quota,
account-deletion and admin flows, the Stripe lifecycle (SDK calls mocked), and Apple JWS
verification (generated certificate chains). Migrations and Postgres-only SQL (`date_trunc` in
the revenue chart) are not covered by the suite; run them against a Postgres instance.
