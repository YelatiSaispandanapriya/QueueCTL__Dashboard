# enqueue_test_jobs.py
import json
from db import enqueue_job, clear_jobs
from datetime import datetime
from uuid import uuid4

# Step 1: Clear old jobs from the database
clear_jobs()
print("Cleared all previous jobs from the queue.\n")

# Step 2: List of job JSON files to enqueue
job_files = [
    "job_basic.json",     # basic job
    "job_fail.json",      # job that fails
    "job_multi_1.json",   # multi-worker job 1
    "job_multi_2.json",   # multi-worker job 2
    "job_slow.json",      # slow job
]

# Step 3: Enqueue jobs with unique IDs and timestamps
for file in job_files:
    try:
        with open(file, "r", encoding="utf-8-sig") as f:
            job = json.load(f)

        # Assign a new unique ID
        job['id'] = str(uuid4())

        # Add timestamps
        now_iso = datetime.utcnow().isoformat()
        job["created_at"] = now_iso
        job["updated_at"] = now_iso

        enqueue_job(job)
        print(f"Enqueued job {job['id']} -> {job['command']}")
    except Exception as e:
        print(f"Failed to enqueue job from {file}: {e}")
