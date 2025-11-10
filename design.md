# QueueCTL Architecture & Design

## 1. Overview
`queuectl` is a CLI-based background job queue system designed to run commands asynchronously with multiple worker processes. It supports retries with exponential backoff, persistent storage, scheduled jobs, and a Dead Letter Queue (DLQ) for failed jobs.

---

## 2. Components

### a. Job Queue
- Jobs are persisted in **SQLite**.
- Each job contains:
  - `id`: Unique identifier
  - `command`: Command to execute
  - `state`: `pending`, `processing`, `completed`, `failed`, `dead`
  - `attempts` & `max_retries`
  - `priority` (higher executes first)
  - `timeout` (optional)
  - `run_at` (optional scheduled execution time)
  - `created_at` / `updated_at`
- Jobs can be enqueued via CLI.

### b. Workers
- Each worker is a Python thread that:
  1. Picks an eligible job (based on state, priority, and `run_at`).
  2. Executes the job command.
  3. Handles success or failure.
  4. Applies exponential backoff for retries.
- Supports multiple workers concurrently without job overlap.
- Graceful shutdown is implemented (finish current job before exiting).

### c. Retry & Backoff
- Failed jobs are retried automatically up to `max_retries`.
- Exponential backoff: `delay = 2^attempts` seconds (configurable).
- Jobs exceeding retries are moved to **DLQ**.

### d. Dead Letter Queue (DLQ)
- Stores permanently failed jobs.
- Jobs in DLQ can be retried manually via CLI.

### e. Configuration
- `queuectl_config.json` stores:
  - `max_retries`
  - `retry_base`
- Configurable via CLI commands (`config set/get`).

### f. Dashboard (Optional)
- Minimal web dashboard using Flask.
- Displays job states: pending, processing, completed, dead.
- Shows `created_at` and `updated_at`.

---

## 3. Data Flow
```
CLI enqueue → SQLite DB → Worker threads → Job execution → Update DB → DLQ if failed
```

---

## 4. Assumptions & Design Choices
- SQLite is used for simplicity and persistence.
- Workers are threads, not separate processes.
- Commands are executed via `subprocess` for compatibility with shell commands.
- Scheduled jobs use `run_at` and are only picked when time <= current time.
- Priority handling is applied when multiple jobs are pending.
- Minimal web dashboard is for monitoring only; no control actions.

---

## 5. Extensibility
- Can switch from SQLite to PostgreSQL for high concurrency.
- Can add metrics and logging for observability.
- Web dashboard can be extended with filtering and real-time updates.

