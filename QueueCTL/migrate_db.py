# migrate_db.py
import sqlite3

DB_FILE = "queuectl.db"

conn = sqlite3.connect(DB_FILE)
cur = conn.cursor()

columns = [
    ("output", "TEXT"),
    ("error", "TEXT"),
    ("timeout", "INTEGER"),
    ("run_at", "TEXT"),
    ("priority", "INTEGER DEFAULT 0")
]

for col, col_type in columns:
    try:
        cur.execute(f"ALTER TABLE jobs ADD COLUMN {col} {col_type}")
        print(f"Added column {col}")
    except sqlite3.OperationalError:
        print(f"Column {col} already exists")

conn.commit()
conn.close()
