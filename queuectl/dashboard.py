from flask import Flask, render_template
from db import get_conn

app = Flask(__name__)

def fetch_jobs():
    conn = get_conn()
    cur = conn.cursor()
    # Order by priority descending, then created_at
    cur.execute("SELECT id, state, attempts, created_at, updated_at, priority FROM jobs ORDER BY priority DESC, created_at")
    jobs = cur.fetchall()
    return jobs

def fetch_stats():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT state, COUNT(*) AS count FROM jobs GROUP BY state")
    rows = cur.fetchall()
    stats = {
        "total": 0,
        "pending": 0,
        "processing": 0,
        "completed": 0,
        "failed": 0,
        "dead": 0
    }
    for row in rows:
        state = row['state'].lower()
        stats[state] = row['count']
        stats['total'] += row['count']
    return stats

@app.route("/")
def index():
    jobs = fetch_jobs()
    stats = fetch_stats()
    return render_template("dashboard.html", jobs=jobs, stats=stats)

def run_dashboard():
    app.run(port=5000, debug=False, use_reloader=False)

if __name__ == "__main__":
    print("Starting QueueCTL Dashboard on http://127.0.0.1:5000")
    run_dashboard()
