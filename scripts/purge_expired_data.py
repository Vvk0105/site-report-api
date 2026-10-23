"""
Retention clean-up. Run on a schedule (cron, a Kubernetes CronJob, or a scheduled container).

    python -m scripts.purge_expired_data              # dry run: prints what would be deleted
    python -m scripts.purge_expired_data --apply      # deletes

Removes:
  * login logs older than --login-log-days (default 365)
  * OTP codes that have expired
  * refresh tokens that have expired or been revoked
"""

import argparse
import asyncio
from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, func, select

from app.db.database import SessionLocal
from app.models.login_log import LoginLog
from app.models.otp import OTPCode
from app.models.refresh_token import RefreshToken


async def run(apply: bool, login_log_days: int) -> None:
    now = datetime.now(timezone.utc)
    login_cutoff = now - timedelta(days=login_log_days)

    targets = {
        "login logs": (LoginLog, LoginLog.login_at < login_cutoff),
        "expired OTP codes": (OTPCode, OTPCode.expires_at < now),
        "expired or revoked refresh tokens": (
            RefreshToken,
            (RefreshToken.expires_at < now) | (RefreshToken.revoked.is_(True)),
        ),
    }

    async with SessionLocal() as db:
        for label, (model, condition) in targets.items():
            count = await db.scalar(select(func.count()).select_from(model).where(condition))
            print(f"{label}: {count} row(s) {'deleted' if apply else 'would be deleted'}")

            if apply and count:
                await db.execute(delete(model).where(condition))

        if apply:
            await db.commit()
        else:
            print("Dry run only. Pass --apply to delete.")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--apply", action="store_true", help="actually delete rows")
    parser.add_argument("--login-log-days", type=int, default=365, help="keep login logs this many days")
    args = parser.parse_args()

    asyncio.run(run(apply=args.apply, login_log_days=args.login_log_days))


if __name__ == "__main__":
    main()
