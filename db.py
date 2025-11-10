import sqlite3
from datetime import datetime

DB_FILE = "queue.db"

def get_conn():
    conn = sqlite3.connect(DB_FILE, detect_types=sqlite3.PARSE_DECLTYPES)
    conn.row_factory = sqlite3.Row
    return conn

# -------------------------------
# Initialize DB
# -------------------------------
def init_db():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS jobs (
            id TEXT PRIMARY KEY,
            command TEXT NOT NULL,
            state TEXT NOT NULL,
            attempts INTEGER NOT NULL,
            max_retries INTEGER NOT NULL,
            timeout INTEGER,
            run_at TEXT,
            priority INTEGER DEFAULT 0,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            output TEXT,
            error TEXT
        )
    """)
    conn.commit()

# -------------------------------
# Enqueue job
# -------------------------------
def enqueue_job(job_data):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO jobs (id, command, state, attempts, max_retries, timeout, run_at, priority, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        job_data['id'],
        job_data['command'],
        job_data['state'],
        job_data['attempts'],
        job_data['max_retries'],
        job_data.get('timeout'),
        job_data.get('run_at'),
        job_data.get('priority', 0),
        job_data['created_at'],
        job_data['updated_at']
    ))
    conn.commit()

# -------------------------------
# Try acquire job for processing
# -------------------------------
def try_acquire_job():
    """
    Atomically acquire one eligible job for processing.
    Returns the job dict if acquired, else None.
    """
    conn = get_conn()
    cur = conn.cursor()

    now_iso = datetime.now().isoformat()

    # Atomically select a pending job with eligible run_at and mark it as processing
    cur.execute("""
        UPDATE jobs
        SET state='processing', updated_at=CURRENT_TIMESTAMP
        WHERE id = (
            SELECT id FROM jobs
            WHERE state='pending'
            AND (run_at IS NULL OR run_at <= ?)
            ORDER BY priority DESC, created_at ASC
            LIMIT 1
        )
        RETURNING *
    """, (now_iso,))
    
    row = cur.fetchone()
    conn.commit()

    if row:
        # Convert to dictionary for worker_loop
        return dict(row)
    return None

    
    # Atomically mark job as processing
    cur.execute("UPDATE jobs SET state='processing', updated_at=CURRENT_TIMESTAMP WHERE id=?", (row['id'],))
    conn.commit()
    return dict(row)


# Mark job completed

def mark_job_completed(job_id, output=None):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        UPDATE jobs
        SET state='completed', output=?, updated_at=CURRENT_TIMESTAMP
        WHERE id=?
    """, (output, job_id))
    conn.commit()


# Mark job failed (retry or DLQ)

def mark_job_failed(job_id, errtxt=None):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT attempts, max_retries FROM jobs WHERE id=?", (job_id,))
    row = cur.fetchone()
    if not row:
        return

    attempts = row['attempts'] + 1
    max_retries = row['max_retries']

    if attempts >= max_retries:
        state = 'dead'
    else:
        state = 'pending'

    cur.execute("""
        UPDATE jobs
        SET attempts=?, state=?, error=?, updated_at=CURRENT_TIMESTAMP
        WHERE id=?
    """, (attempts, state, errtxt, job_id))
    conn.commit()


# Mark job back to pending (for scheduled jobs)

def mark_job_pending(job_id):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        UPDATE jobs
        SET state='pending', updated_at=CURRENT_TIMESTAMP
        WHERE id=?
    """, (job_id,))
    conn.commit()



# Clear all jobs (for testing)

def clear_jobs():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("DELETE FROM jobs")
    conn.commit()
