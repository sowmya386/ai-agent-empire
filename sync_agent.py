# sync_agent.py — handles offline/online sync
# pip install supabase schedule requests
import sqlite3
import json
import os
import schedule
import time
import requests
from supabase import create_client

SUPABASE_URL = os.environ.get('SUPABASE_URL')    # Free at supabase.com
SUPABASE_KEY = os.environ.get('SUPABASE_ANON_KEY')

def get_supabase_client():
    if SUPABASE_URL and SUPABASE_KEY:
        try:
            return create_client(SUPABASE_URL, SUPABASE_KEY)
        except Exception as e:
            print(f"Failed to initialize Supabase client: {e}")
    return None

def check_online():
    try:
        # Ping Cloudflare DNS (1.1.1.1) to check internet connectivity
        requests.get('https://1.1.1.1', timeout=3)
        return True
    except:
        return False

def init_db():
    conn = sqlite3.connect('agent_empire.db')
    # Initialize basic task structure if not present
    conn.execute('''CREATE TABLE IF NOT EXISTS tasks (
        id INTEGER PRIMARY KEY,
        agent TEXT, task TEXT, status TEXT,
        created_at TEXT, done_at TEXT)''')
    # Ensure synced column exists
    try:
        conn.execute('ALTER TABLE tasks ADD COLUMN synced INTEGER DEFAULT 0')
    except sqlite3.OperationalError:
        pass # Already exists
    conn.commit()
    return conn

def sync_to_cloud():
    print(f"[{datetime_now()}] Checking connection for cloud sync...")
    if not check_online():
        print("Device is offline. Cache saved. Postponing cloud sync.")
        return

    supabase_client = get_supabase_client()
    if not supabase_client:
        print("Supabase credentials not configured. Local database active only.")
        return

    conn = init_db()
    cursor = conn.cursor()

    try:
        # 1. Push locally completed/updated tasks that are not synced yet
        local_tasks = cursor.execute(
            "SELECT id, agent, task, status, created_at, done_at FROM tasks WHERE synced = 0"
        ).fetchall()
        
        for task in local_tasks:
            local_id, agent, task_name, status, created_at, done_at = task
            payload = {
                "agent": agent,
                "task": task_name,
                "status": status,
                "created_at": created_at,
                "done_at": done_at,
                "device_id": os.environ.get('COMPUTERNAME', 'local_device')
            }
            res = supabase_client.table('tasks').upsert(payload).execute()
            if res.data:
                conn.execute("UPDATE tasks SET synced = 1 WHERE id = ?", (local_id,))
                print(f"Synced local task {local_id} to cloud.")
        conn.commit()

        # 2. Pull new tasks submitted from Cloud/Dashboard
        device_id = os.environ.get('COMPUTERNAME', 'local_device')
        res = supabase_client.table('tasks').select("*").eq("device_id", device_id).eq("status", "pending_cloud").execute()
        
        for cloud_task in res.data:
            cloud_id = cloud_task.get('id')
            agent = cloud_task.get('agent')
            task_name = cloud_task.get('task')
            created_at = cloud_task.get('created_at')
            
            existing = cursor.execute(
                "SELECT id FROM tasks WHERE agent = ? AND task = ? AND created_at = ?", 
                (agent, task_name, created_at)
            ).fetchone()
            
            if not existing:
                cursor.execute(
                    "INSERT INTO tasks (agent, task, status, created_at, done_at, synced) VALUES (?, ?, 'pending', ?, NULL, 1)",
                    (agent, task_name, created_at)
                )
                print(f"Pulled cloud task: {agent} -> {task_name}")
                
            # Mark task as pending locally on cloud
            supabase_client.table('tasks').update({"status": "pending"}).eq("id", cloud_id).execute()
        conn.commit()

    except Exception as e:
        print(f"Sync failed: {e}")
    finally:
        conn.close()

def datetime_now():
    from datetime import datetime
    return datetime.now().isoformat()

if __name__ == "__main__":
    init_db()
    if os.environ.get('RUN_ONCE') or os.environ.get('GITHUB_ACTIONS'):
        print("Single execution sync mode active via GITHUB_ACTIONS.")
        sync_to_cloud()
    else:
        print("Sync agent daemon started.")
        sync_to_cloud()
        schedule.every(5).minutes.do(sync_to_cloud)
        while True:
            schedule.run_pending()
            time.sleep(60)
