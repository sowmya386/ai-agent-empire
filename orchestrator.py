# orchestrator.py — run once, keeps running forever
import sqlite3
import time
import subprocess
import schedule
from datetime import datetime

def init_db():
    conn = sqlite3.connect('agent_empire.db')
    conn.execute('''CREATE TABLE IF NOT EXISTS tasks (
        id INTEGER PRIMARY KEY,
        agent TEXT, task TEXT, status TEXT,
        created_at TEXT, done_at TEXT)''')
    conn.commit()
    return conn

def add_task(conn, agent, task):
    conn.execute("INSERT INTO tasks VALUES (NULL,?,?,'pending',?,NULL)",
                 (agent, task, datetime.now().isoformat()))
    conn.commit()

def run_scheduled_tasks(conn):
    now = datetime.now()
    # YouTube: 1 video per day at 9am
    if now.hour == 9 and now.minute < 30:
        add_task(conn, 'youtube', 'generate_and_upload_video')
    # Instagram: 3 posts per day
    if now.hour in [8, 13, 19] and now.minute < 30:
        add_task(conn, 'instagram', 'create_and_post')
    # Stock scan: every 30 minutes during market hours
    if 9 <= now.hour <= 15:
        add_task(conn, 'stocks', 'scan_and_signal')

def dispatch_tasks(conn):
    tasks = conn.execute(
        "SELECT * FROM tasks WHERE status='pending'").fetchall()
    for task in tasks:
        print(f"Running: {task[1]} → {task[2]}")
        subprocess.Popen(['python', f'{task[1]}_agent.py', task[2]])
        conn.execute("UPDATE tasks SET status='running' WHERE id=?", (task[0],))
    conn.commit()

if __name__ == "__main__":
    conn = init_db()
    print("Orchestrator brain initialized. Running background daemon...")
    schedule.every(30).minutes.do(lambda: run_scheduled_tasks(conn))
    schedule.every(5).minutes.do(lambda: dispatch_tasks(conn))
    
    # Run immediate scan on start
    run_scheduled_tasks(conn)
    dispatch_tasks(conn)
    
    while True:
        schedule.run_pending()
        time.sleep(60)