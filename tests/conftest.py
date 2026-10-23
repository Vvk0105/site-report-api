import os
import tempfile

# Settings are read at import time, so provide safe test values before any app import.
# Real environment variables still win if they are set.
_TEST_ENV = {
    "DATABASE_URL": "postgresql+asyncpg://test:test@localhost:5432/test",
    "SECRET_KEY": "test-secret-key-that-is-long-enough-for-hs256",
    "ALGORITHM": "HS256",
    "ADMIN_EMAIL": "admin@example.com",
    "ADMIN_PASSWORD": "test-admin-password",
    "SMTP_HOST": "smtp.example.com",
    "SMTP_PORT": "587",
    "SMTP_USERNAME": "smtp-user",
    "SMTP_PASSWORD": "smtp-pass",
    "SMTP_FROM": "noreply@example.com",
    "SMTP_SSL": "false",
    "STRIPE_SECRET_KEY": "sk_test_dummy",
    "STRIPE_PUBLISHABLE_KEY": "pk_test_dummy",
    "STRIPE_WEBHOOK_SECRET": "whsec_dummy",
}

for key, value in _TEST_ENV.items():
    os.environ.setdefault(key, value)

# The suite runs against a throwaway SQLite database. Real environment variables
# are never used for the database during tests.
_TEST_DB = os.path.join(tempfile.mkdtemp(prefix="site-report-tests-"), "test.db")
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{_TEST_DB}"
