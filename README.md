# QueueCTL - CLI-based Background Job Queue System

## Overview

**QueueCTL** is a CLI-based background job queue system designed to manage, schedule, and execute jobs reliably. It supports multiple workers, automatic retries with exponential backoff, and a Dead Letter Queue (DLQ) for permanently failed jobs. The system provides persistent storage and a minimal web dashboard for monitoring.

---

## Setup Instructions

### Prerequisites
- Python 3.10+
- SQLite (comes with Python standard library)
- Recommended: Use a virtual environment

### Installation
```bash
# Clone repository
git clone <repository_url>
cd queuectl

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
.venv\Scripts\activate     # Windows

# Install dependencies
pip install -r requirements.txt
```

### Initialize Database
Database initializes automatically on first run.

---

## Usage Examples

### Enqueue a Job
```bash
python queuectl.py enqueue job_basic.json --timeout 10 --priority 2 --run-at "2025-11-10T16:30:00"
```

### Start Workers
```bash
python queuectl.py worker start --count 3
```

### Stop Workers
- Stop gracefully with `Ctrl+C`.

### List Jobs
```bash
python queuectl.py list
python queuectl.py list --state pending
```

### Check Job Status Summary
```bash
python queuectl.py status
```

### Dead Letter Queue
```bash
python queuectl.py dlq list
python queuectl.py dlq retry job_id
```

### Configuration
```bash
python queuectl.py config set max_retries 5
python queuectl.py config get max_retries
```


![My Image](QueueCTL/images/image1.png)

Failed job retries with backoff and moves to DLQ.
![Failed job retries with backoff and moves to DLQ.](outputs/Failed job retries with backoff and moves to DLQ.)

Multiple workers process jobs without overlap.
![Multiple workers process jobs without overlap.](outputs/Multiple workers process jobs without overlap.)

Invalid commands fail gracefully.
![Invalid commands fail gracefully.](outputs/Invalid commands fail gracefully.)

Job data survives restart.
![Job data survives restart.](outputs/Job data survives restart.)



---

## Architecture Overview

![Design](QueueCTL/Images/Design.jpg)


### Job Lifecycle
| State        | Description |
| ------------ | ----------- |
| `pending`    | Waiting to be picked by a worker |
| `processing` | Currently executing |
| `completed`  | Successfully executed |
| `failed`     | Failed but retryable |
| `dead`       | Permanently failed (DLQ) |

### Data Persistence
- Jobs are stored in SQLite (`jobs.db`) for persistence across restarts.

### Worker Logic
- Multiple workers execute jobs in parallel.
- Locks prevent duplicate job execution.
- Failed jobs are retried automatically with exponential backoff.
- Jobs moved to DLQ after exceeding `max_retries`.
- Supports **timeouts**, **priorities**, and **scheduled/delayed execution** (`run_at`).

### Minimal Web Dashboard
- Provides real-time job overview with state, attempts, created/updated times, and priority.
- Professional summary header with total counts for each state.

---

## Assumptions & Trade-offs

- **Python subprocess commands** are used for job execution; shell commands must be valid.
- **Timezones**: ISO format is assumed in local system time.
- **Simplification**: No distributed worker cluster; all workers run locally.
- **Retry logic** uses exponential backoff (`base^attempts`) with a configurable maximum.
- **Dashboard refresh**: Manual or automatic refresh can be added.

---

## Testing Instructions

### 1. Basic Job
- Enqueue a simple job (`echo "Hello World"`) and verify `completed` state.

### 2. Failed Job & DLQ
- Enqueue an invalid command (`not_a_real_command`) and verify:
  - Retries with exponential backoff
  - Moves to DLQ after `max_retries`

### 3. Multiple Workers
- Start multiple workers (`--count 3`) and ensure jobs are not processed multiple times simultaneously.

### 4. Job Timeout
- Enqueue a command that sleeps longer than timeout; verify job fails with timeout.

### 5. Priority Queue
- Enqueue jobs with different priorities; verify higher priority jobs are processed first.

### 6. Scheduled/Delayed Jobs
- Enqueue a job with `--run-at` in the future; verify worker picks it up only after the scheduled time.

### 7. Persistence
- Stop and restart workers; verify pending jobs are retained and processed after restart.

### 8. Dashboard
- Start web dashboard: verify it displays correct summary and job table (without command column).

---

## Bonus Features Implemented

- Job timeout handling
  ![Job timeout handling](outputs/Job timeout handling)

- Job priority queues
![Job priority queues](outputs/Job priority queues)
  
- Scheduled/delayed jobs (`run_at`)

![Scheduleddelayed jobs (run_at)-Before time](outputs/Scheduleddelayed jobs (run_at)-Before time)
![Scheduleddelayed jobs (run_at)-after time](outputs/Scheduleddelayed jobs (run_at)-after time)

- Minimal web dashboard

![Minimal web dashboard](outputs/Minimal web dashboard)

---

## Example Job JSON

```json
{
    "id": "job_basic",
    "command": "python -c \"import time; time.sleep(10)\""
}
```
## Recording Link
https://drive.google.com/file/d/1oRrbCC4-AH5o39YOrZNGANpbneWYzgU4/view?usp=drivesdk 
