# enqueue_job.py
import json
from db import enqueue_job
from datetime import datetime
import sys

if len(sys.argv) != 2:
    print("Usage: python enqueue_job.py <job_json_file>")
    sys.exit(1)

job_file = sys.argv[1]

try:
    # Read JSON safely (handle BOM)
    with open(job_file, encoding="utf-8-sig") as f:
        job = json.load(f)

    # Generate unique readable job ID: jobname_dd-mm-yyyy-HHMMSS
    timestamp = datetime.now().strftime("%d-%m-%Y-%H%M%S")
    job_name = job.get("id", "job")
    job["id"] = f"{job_name}_{timestamp}"

    # Add timestamps in YYYY-MM-DD HH:MM:SS format
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    job["created_at"] = now
    job["updated_at"] = now

    # Default values
    job.setdefault("state", "pending")
    job.setdefault("attempts", 0)
    job.setdefault("max_retries", 3)

    enqueue_job(job)
    print(f"Enqueued job {job['id']} -> {job['command']}")

except Exception as e:
    print(f"Failed to enqueue job: {e}")
