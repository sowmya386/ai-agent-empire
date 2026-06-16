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
    
    # Initialize watchlist and stock signals
    conn.execute('''CREATE TABLE IF NOT EXISTS watchlist (
        symbol TEXT PRIMARY KEY)''')
    conn.execute('''CREATE TABLE IF NOT EXISTS stock_signals (
        symbol TEXT PRIMARY KEY,
        price REAL,
        rsi REAL,
        macd REAL,
        signal TEXT,
        updated_at TEXT)''')
    
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM watchlist")
    if cursor.fetchone()[0] == 0:
        default_watchlist = [('HDFCBANK.NS',), ('RELIANCE.NS',), ('INFY.NS',), ('TCS.NS',), ('ICICIBANK.NS',)]
        cursor.executemany("INSERT OR IGNORE INTO watchlist (symbol) VALUES (?)", default_watchlist)
        conn.commit()
        
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

        # 3. Pull watchlist from Supabase to local SQLite
        try:
            res_wl = supabase_client.table('watchlist').select("*").execute()
            if res_wl.data is not None:
                cloud_symbols = [row['symbol'] for row in res_wl.data]
                if cloud_symbols:
                    # Sync cloud symbols to local
                    placeholders = ','.join('?' for _ in cloud_symbols)
                    cursor.execute(f"DELETE FROM watchlist WHERE symbol NOT IN ({placeholders})", cloud_symbols)
                    for sym in cloud_symbols:
                        cursor.execute("INSERT OR IGNORE INTO watchlist (symbol) VALUES (?)", (sym,))
                    conn.commit()
                    print("Synced watchlist from cloud.")
        except Exception as e:
            print(f"Watchlist cloud sync skipped/failed: {e}")

        # 4. Push local stock signals to Supabase
        try:
            local_signals = cursor.execute("SELECT symbol, price, rsi, macd, signal, updated_at FROM stock_signals").fetchall()
            for sig in local_signals:
                sym, price, rsi, macd, signal_val, updated_at = sig
                payload = {
                    "symbol": sym,
                    "price": price,
                    "rsi": rsi,
                    "macd": macd,
                    "signal": signal_val,
                    "updated_at": updated_at
                }
                supabase_client.table('stock_signals').upsert(payload).execute()
            print("Synced stock signals to cloud.")
        except Exception as e:
            print(f"Stock signals cloud sync skipped/failed: {e}")

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
