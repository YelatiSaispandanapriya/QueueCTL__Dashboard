import click
import json
import os
import time
import threading
from datetime import datetime
from db import (
    init_db, enqueue_job, try_acquire_job,
    mark_job_completed, mark_job_failed, mark_job_pending, get_conn
)
from worker import worker_loop

# ------------------------------
# Initialization
# ------------------------------
init_db()
WORKERS = []

CONFIG_FILE = "queuectl_config.json"
DEFAULT_CONFIG = {"max_retries": 3, "retry_base": 2}

def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE) as f:
            return json.load(f)
    return DEFAULT_CONFIG.copy()

def save_config(config):
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f)

CONFIG = load_config()

# ------------------------------
# CLI
# ------------------------------
@click.group()
def cli():
    pass

# ------------------------------
# Enqueue Command
# ------------------------------
@cli.command("enqueue")
@click.argument("job_json_file")
@click.option("--timeout", type=int, default=None, help="Timeout in seconds")
@click.option("--run-at", default=None, help="Schedule job at future time (ISO format)")
@click.option("--priority", type=int, default=None, help="Job priority (higher executes first)")
def enqueue(job_json_file, timeout, run_at, priority):
    """Add a new job to the queue from a JSON file"""
    try:
        with open(job_json_file, encoding="utf-8-sig") as f:
            job_data = json.load(f)

        timestamp_str = datetime.now().strftime("%d-%m-%Y-%H%M%S")
        job_name = job_data.get("id", "job")
        job_id = f"{job_name}_{timestamp_str}"
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Normalize run_at format
        if run_at:
            try:
                job_data["run_at"] = datetime.fromisoformat(run_at).replace(microsecond=0).isoformat()
            except ValueError:
                click.echo(f"Invalid --run-at format: {run_at}. Use ISO format like '2025-11-10T16:30:00'.")
                return
        else:
            job_data["run_at"] = job_data.get("run_at")

        job_data.update({
            "id": job_id,
            "created_at": now_str,
            "updated_at": now_str,
            "max_retries": CONFIG.get("max_retries", 3),
            "attempts": 0,
            "state": "pending",
            "timeout": timeout if timeout is not None else job_data.get("timeout"),
            "priority": priority if priority is not None else job_data.get("priority", 0)
        })

        enqueue_job(job_data)
        click.echo(f"Enqueued job {job_id} -> {job_data.get('command')}")
    except Exception as e:
        click.echo(f"Failed to enqueue job: {e}")

# ------------------------------
# Worker Commands
# ------------------------------
@cli.group()
def worker():
    """Manage workers"""
    pass

@worker.command("start")
@click.option("--count", default=1, help="Number of workers")
def worker_start(count):
    """Start workers"""
    global WORKERS

    def start_worker_thread(wid):
        worker_loop(worker_id=wid)

    for i in range(count):
        t = threading.Thread(target=start_worker_thread, args=(i+1,), daemon=True)
        WORKERS.append(t)
        t.start()
    click.echo(f"Started {count} worker(s). Press Ctrl+C to stop.")

    try:
        while any(t.is_alive() for t in WORKERS):
            time.sleep(1)
    except KeyboardInterrupt:
        click.echo("Shutting down workers...")
        for t in WORKERS:
            t.join()

@worker.command("stop")
def worker_stop():
    click.echo("Stopping workers is handled via Ctrl+C in 'worker start'")

# ------------------------------
# List Command
# ------------------------------
@cli.command("list")
@click.option("--state", default=None, help="Filter jobs by state")
def list_jobs(state):
    conn = get_conn()
    cur = conn.cursor()
    if state:
        cur.execute("SELECT * FROM jobs WHERE state=? ORDER BY priority DESC, created_at", (state,))
    else:
        cur.execute("SELECT * FROM jobs ORDER BY priority DESC, created_at")
    rows = cur.fetchall()
    if not rows:
        click.echo("No jobs found")
        return
    click.echo(f"{'ID':30} {'State':10} {'Attempts':8} {'Created At':19} {'Updated At':19} {'Priority':8} {'Command'}")
    click.echo("-"*120)
    for row in rows:
        click.echo(f"{row['id']:30} {row['state']:10} {row['attempts']:8} {row['created_at']:19} {row['updated_at']:19} {row['priority']:8} {row['command']}")

# ------------------------------
# Status Command
# ------------------------------
@cli.command("status")
def status():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT state, COUNT(*) FROM jobs GROUP BY state")
    counts = {row[0]: row[1] for row in cur.fetchall()}
    click.echo("Job Summary:")
    for state in ["pending", "processing", "completed", "failed", "dead"]:
        click.echo(f"  {state}: {counts.get(state,0)}")
    click.echo(f"Active workers: {len(WORKERS)}")

# ------------------------------
# DLQ Commands
# ------------------------------
@cli.group()
def dlq():
    """Manage Dead Letter Queue"""
    pass

@dlq.command("list")
def dlq_list():
    """List DLQ jobs"""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM jobs WHERE state='dead' ORDER BY updated_at")
    rows = cur.fetchall()
    if not rows:
        click.echo("DLQ is empty")
        return
    click.echo(f"{'ID':30} {'State':10} {'Command':40} {'Attempts':8} {'Updated At':19} {'Error'}")
    click.echo("-"*120)
    for row in rows:
        click.echo(f"{row['id']:30} {row['state']:10} {row['command'][:40]:40} {row['attempts']:8} {row['updated_at']:19} {row['error']}")

@dlq.command("retry")
@click.argument("job_id")
def dlq_retry(job_id):
    """Retry a job from DLQ"""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM jobs WHERE id=? AND state='dead'", (job_id,))
    row = cur.fetchone()
    if not row:
        click.echo(f"No dead job found with id {job_id}")
        return
    cur.execute(
        "UPDATE jobs SET state='pending', attempts=0, updated_at=CURRENT_TIMESTAMP WHERE id=?",
        (job_id,)
    )
    conn.commit()
    click.echo(f"Job {job_id} moved back to queue for retry")

# ------------------------------
# Config Commands
# ------------------------------
@cli.group()
def config():
    """Manage configuration"""
    pass

@config.command("set")
@click.argument("key")
@click.argument("value")
def config_set(key, value):
    CONFIG[key] = int(value) if value.isdigit() else value
    save_config(CONFIG)
    click.echo(f"Config {key} set to {value}")

@config.command("get")
@click.argument("key")
def config_get(key):
    val = CONFIG.get(key)
    click.echo(f"{key} = {val}")

# ------------------------------
# Main
# ------------------------------
if __name__ == "__main__":
    cli()
