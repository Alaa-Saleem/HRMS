import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from sqlalchemy import text
from app.database import engine

print("Fixing audit_events columns...")
with engine.connect() as conn:
    is_postgres = "postgresql" in str(engine.url)
    if is_postgres:
        conn.execute(text("ALTER TABLE audit_events ADD COLUMN IF NOT EXISTS actor_platform_user_id INTEGER REFERENCES platform_users(id) ON DELETE SET NULL;"))
        conn.commit()
    else:
        try:
            conn.execute(text("ALTER TABLE audit_events ADD COLUMN actor_platform_user_id INTEGER REFERENCES platform_users(id);"))
            conn.commit()
        except Exception as e:
            print("SQLite note:", e)

print("✓ Done.")
