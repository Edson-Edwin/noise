"""Delete expired data in bounded batches; one-shot for Render cron."""
import argparse
import os
import time
from sqlalchemy import create_engine, text

def prune():
    days = int(os.environ.get("RETENTION_DAYS", "30"))
    if not 1 <= days <= 3650:
        raise ValueError("RETENTION_DAYS must be 1..3650")
    url = os.environ["DATABASE_URL"].replace("postgres://", "postgresql+psycopg://", 1).replace("postgresql://", "postgresql+psycopg://", 1)
    engine = create_engine(url, connect_args={"connect_timeout": 5, "options": "-c statement_timeout=30000"})
    total = 0
    try:
        while True:
            with engine.begin() as db:
                count = db.execute(text("DELETE FROM readings WHERE id IN (SELECT id FROM readings WHERE created_at < now() - make_interval(days => :days) ORDER BY created_at LIMIT 10000)"), {"days": days}).rowcount
            total += count
            if count < 10000:
                break
        print(f"Retention complete: {total} expired readings removed", flush=True)
    finally:
        engine.dispose()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--loop", action="store_true")
    args = parser.parse_args()
    while True:
        prune()
        if not args.loop:
            break
        time.sleep(86400)
