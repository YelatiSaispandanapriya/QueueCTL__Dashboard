import subprocess
import threading
import time
import signal
from datetime import datetime
from db import try_acquire_job, mark_job_completed, mark_job_failed, mark_job_pending, get_conn

shutdown_flag = False
MAX_BACKOFF = 5  # Maximum backoff in seconds

def signal_handler(sig, frame):
    global shutdown_flag
    print(f"{timestamp()} Worker received shutdown signal, finishing current job then exiting...")
    shutdown_flag = True

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

def timestamp():
    """Return current timestamp in HH:MM:SS format."""
    return datetime.now().strftime("[%H:%M:%S]")

def worker_loop(worker_id):
    global shutdown_flag
    while not shutdown_flag:
        # Fetch the next eligible job (highest priority, run_at <= now)
        job = try_acquire_job()
        if not job:
            time.sleep(1)
            continue

        job_id = job['id']
        command = job['command']
        attempts = job['attempts']
        max_retries = job['max_retries']
        timeout = job.get('timeout')
        run_at = job.get('run_at')

        # Check run_at for scheduled jobs
        if run_at:
            try:
                run_time = datetime.fromisoformat(run_at)
                now = datetime.now()
                if now < run_time:
                    # Not yet time, revert to pending
                    mark_job_pending(job_id)
                    time.sleep(1)
                    continue
            except Exception as e:
                print(f"{timestamp()} [worker {worker_id}] Invalid run_at format for job {job_id}: {e}")

        print(f"{timestamp()} [worker {worker_id}] picked job {job_id} (attempt {attempts}/{max_retries}): {command}")

        try:
            completed_process = subprocess.run(
                command, shell=True, capture_output=True, text=True, timeout=timeout
            )
            output = completed_process.stdout.strip()

            if completed_process.returncode == 0:
                print(f"{timestamp()} [worker {worker_id}] {output}")
                mark_job_completed(job_id, output=output)
                print(f"{timestamp()} [worker {worker_id}] job {job_id} completed successfully. Waiting for next job...")

            else:
                err_output = completed_process.stderr.strip() or f"exit code {completed_process.returncode}"
                print(f"{timestamp()} [worker {worker_id}] job {job_id} failed: {err_output}")
                mark_job_failed(job_id, errtxt=err_output)
                handle_retry(worker_id, job_id, attempts, max_retries)

        except subprocess.TimeoutExpired:
            print(f"{timestamp()} [worker {worker_id}] job {job_id} timed out after {timeout}s")
            mark_job_failed(job_id, errtxt=f"timeout after {timeout}s")
            handle_retry(worker_id, job_id, attempts, max_retries)

        except Exception as e:
            print(f"{timestamp()} [worker {worker_id}] job {job_id} failed with exception: {e}")
            mark_job_failed(job_id, errtxt=str(e))
            handle_retry(worker_id, job_id, attempts, max_retries)

    print(f"{timestamp()} [worker {worker_id}] exiting")


def handle_retry(worker_id, job_id, attempts, max_retries):
    """Handles retry logic with exponential backoff."""
    updated_attempts = attempts + 1
    sleep_time = min(2 ** updated_attempts, MAX_BACKOFF)

    # Check job state to decide DLQ
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT state FROM jobs WHERE id=?", (job_id,))
    row = cur.fetchone()
    job_state = row['state'] if row else 'failed'

    if job_state == 'dead':
        print(f"{timestamp()} [worker {worker_id}] job {job_id} reached max retries and moved to DLQ")
    else:
        print(f"{timestamp()} [worker {worker_id}] retrying job {job_id}: attempt {updated_attempts} of {max_retries}, waiting {sleep_time}s before next try...")
        time.sleep(sleep_time)


def start_workers(count=1):
    threads = []
    for i in range(1, count + 1):
        t = threading.Thread(target=worker_loop, args=(i,), daemon=True)
        t.start()
        threads.append(t)
        print(f"{timestamp()} [worker {i}] started")
    print(f"{timestamp()} Started {count} worker(s). Press Ctrl+C to stop.")
    for t in threads:
        t.join()
