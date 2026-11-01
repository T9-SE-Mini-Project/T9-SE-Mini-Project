"""Command-line tasks for operators.

    python -m src.backend.cli create-admin --email admin@example.com
    python -m src.backend.cli expire-units --actor-id 1
    python -m src.backend.cli send-reminders
    python -m src.backend.cli seed-demo

`create-admin` creates the first admin, who can then create other accounts through
POST /api/admin/accounts. `expire-units` and `send-reminders` are meant to be run on a
schedule (e.g. cron, daily / hourly). `seed-demo` fills a local database with demo
accounts and data (development only).
"""
from __future__ import annotations

import argparse
import getpass
import sys
from datetime import timedelta

from .auth.accounts import AccountError, create_account
from .config import load_app_settings
from .database import create_all_tables, create_db_engine, create_session_factory
from .demo import DEMO_PASSWORD, seed_demo
from .drives.service import send_due_reminders
from .inventory.service import expire_blood_units
from .notifications import LoggingNotifier


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m src.backend.cli", description="BBMS operator tasks")
    commands = parser.add_subparsers(dest="command", required=True)

    admin = commands.add_parser("create-admin", help="create an admin account")
    admin.add_argument("--email", required=True)

    expire = commands.add_parser("expire-units", help="mark expired blood units (BLOOD-14)")
    expire.add_argument("--actor-id", type=int, required=True, help="staff/admin account ID recorded in the audit log")

    commands.add_parser("send-reminders", help="send due drive slot reminders (BBS-F-042)")
    commands.add_parser("seed-demo", help="add demo accounts and sample data (development only)")

    args = parser.parse_args(argv)
    settings = load_app_settings()
    engine = create_db_engine(settings.database_url)
    if settings.create_tables:
        create_all_tables(engine)
    session_factory = create_session_factory(engine)

    with session_factory() as db:
        if args.command == "create-admin":
            password = getpass.getpass("Password (min 8 characters): ")
            if password != getpass.getpass("Repeat password: "):
                print("Passwords do not match.", file=sys.stderr)
                return 1
            try:
                account = create_account(db, args.email, password, "admin")
            except AccountError as exc:
                print(exc, file=sys.stderr)
                return 1
            print(f"Created admin account {account.id} ({account.email}).")
        elif args.command == "expire-units":
            count = expire_blood_units(db, actor_id=args.actor_id)
            print(f"Marked {count} unit(s) as expired.")
        elif args.command == "send-reminders":
            run = send_due_reminders(db, LoggingNotifier(), timedelta(hours=settings.reminder_window_hours))
            print(f"Sent {len(run.booking_ids)} reminder(s).")
        elif args.command == "seed-demo":
            accounts = seed_demo(db)
            print(f"Demo accounts (password: {DEMO_PASSWORD}):")
            for email, role in accounts:
                print(f"  {role:<17} {email}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
