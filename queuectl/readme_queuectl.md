# QueueCTL

QueueCTL is a lightweight Python-based CLI tool for job queue management with support for persistent storage, multiple workers, retry logic, and a Dead Letter Queue (DLQ).

---

## 1. Setup Instructions

1. Clone the repository:
```powershell
git clone <repo-url>
cd queuectl
```

2. Create and activate a virtual environment:
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1    # Windows PowerShell
source .venv/bin/activate       # Linux / Mac
```

3. Install dependencies (if any):
```powershell
pip install -r requirements.txt
```

4. Initialize the database:
```powershell
python -c "from db import init_db; init_db()"
```

---

## 2. Usage Examples

### Enqueue a Job
```powershell
python -c "import json, datetime; from db import enqueue_job; job=json.load(open('job1.json')); job['created_at']=job['updated_at']=datetime.datetime.now().isoformat(); enqueue_job(job)"
```

### Start Workers
Start 2 workers to process jobs:
```powershell
python queuectl.py worker start --count 2
```

### List Jobs
List all jobs:
```powershell
python queuectl.py list
```

List completed jobs:
```powershell
python queuectl.py list --state completed
```

List pending jobs:
```powershell
python queuectl.py list --state pending
```

### Dead Letter Queue (DLQ)
View jobs that failed all retries:
```powershell
python queuectl.py dlq list
```

---

## 3. Architecture Overview

- **Job Storage:** SQLite database (`queuectl.db`) with `jobs` table storing job ID, command, state, attempts, timestamps.
- **Worker Logic:**
  - Picks jobs that are `pending` or `failed`.
  - Executes job command via `subprocess`.
  - Marks job `completed` on success.
  - Retries failed jobs with exponential backoff.
  - Moves jobs to DLQ if `max_retries` exceeded.
- **CLI Interface:** Provides commands for listing jobs, enqueuing jobs, starting workers, and viewing DLQ.

**Job Lifecycle Diagram:**

```
pending --> processing --> completed
        \
         --> failed --> retry (backoff) --> DLQ if max_retries
```

---

## 4. Assumptions & Trade-offs

- Commands are executed in the shell (`subprocess`) — no sandboxing, so potentially unsafe commands should be avoided.
- Backoff for failed jobs is configurable but shortened to 1s for testing.
- SQLite is used for simplicity; for production, a more robust DB (Postgres, MySQL, etc.) may be preferred.
- Only minimal concurrency handling is implemented; two workers may read the same job if timing is extremely tight (rare).

---

## 5. Testing Instructions

Manually verify the following scenarios:

1. **Basic Job Completion**
   - Enqueue a simple command (e.g., `echo Hello`)  
   - Start a worker  
   - Verify it appears as `completed`:
     ```powershell
     python queuectl.py list --state completed
     ```

2. **Failed Job Retries & DLQ**
   - Enqueue a job with an invalid command  
   - Start a worker  
   - Observe retry attempts in the worker console  
   - Verify it appears in DLQ after max retries:
     ```powershell
     python queuectl.py dlq list
     ```

3. **Multiple Workers without Overlap**
   - Enqueue multiple jobs  
   - Start multiple workers (`--count 2`)  
   - Confirm each job is picked by only one worker at a time

4. **Invalid Commands Fail Gracefully**
   - Enqueue a job with a non-existent command  
   - Confirm worker logs show the failure without crashing

5. **Job Data Survives Restart**
   - Stop all workers  
   - Restart workers  
   - Confirm pending/failed jobs are resumed properly

