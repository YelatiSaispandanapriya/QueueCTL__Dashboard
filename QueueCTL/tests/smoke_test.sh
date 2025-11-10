#!/usr/bin/env bash
set -e
# Make sure virtualenv is activated and you ran pip install

# 1) Clean DB
rm -f queuectl.db
python3 -c "from db import init_db; init_db(); print('DB init done')"

# 2) Enqueue a successful job and a failing job
python3 queuectl.py enqueue '{"id":"job-success","command":"echo hello && exit 0"}'
python3 queuectl.py enqueue '{"id":"job-fail","command":"bash -c \"exit 2\"","max_retries":2}'

# 3) Start one worker in background
python3 -c "from multiprocessing import Process; import worker, time; p=Process(target=worker.worker_loop, args=(1,2)); p.start(); print('worker pid', p.pid); time.sleep(10); p.terminate()"

# 4) Check status
python3 queuectl.py status
python3 queuectl.py list --state completed || true
python3 queuectl.py list --state failed || true
python3 queuectl.py dlq list || true

echo "Smoke test done"
