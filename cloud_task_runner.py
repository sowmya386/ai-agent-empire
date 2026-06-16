import os
import subprocess
from supabase import create_client

SUPABASE_URL = os.environ.get('SUPABASE_URL')
SUPABASE_KEY = os.environ.get('SUPABASE_ANON_KEY')

def main():
    if not SUPABASE_URL or not SUPABASE_KEY:
        print("Supabase credentials not configured. Exiting.")
        return

    try:
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    except Exception as e:
        print(f"Failed to connect to Supabase: {e}")
        return
    
    # Fetch pending tasks queued for the cloud runner
    try:
        res = supabase.table('tasks').select("*").eq("device_id", "cloud").eq("status", "pending").execute()
    except Exception as e:
        print(f"Error fetching tasks from Supabase: {e}")
        return
    
    if not res.data:
        print("No pending cloud tasks found.")
        return

    for task in res.data:
        task_id = task.get('id')
        agent = task.get('agent')
        directive = task.get('task')
        print(f"Executing cloud task #{task_id}: {agent} -> {directive}")
        
        # Mark task as running on Supabase
        supabase.table('tasks').update({"status": "running"}).eq("id", task_id).execute()
        
        try:
            # Map agent names to files
            if agent == "stocks":
                script_name = "stock_agent.py"
            elif agent == "website":
                script_name = "web_builder_agent.py"
            else:
                script_name = f"{agent}_agent.py"
                
            allowed_scripts = ["stock_agent.py", "youtube_agent.py", "instagram_agent.py", "web_builder_agent.py", "laptop_controller.py", "sync_agent.py"]
            
            if script_name in allowed_scripts:
                # Execute agent script as subprocess
                result = subprocess.run(['python', script_name, directive], capture_output=True, text=True, check=True)
                print(f"Task #{task_id} completed successfully. Logs:\n{result.stdout}")
                
                # Mark as completed
                supabase.table('tasks').update({
                    "status": "completed", 
                    "done_at": datetime_now()
                }).eq("id", task_id).execute()
            else:
                raise ValueError(f"Unauthorized or unknown script action: {script_name}")
                
        except Exception as e:
            error_msg = str(e)
            if hasattr(e, 'stderr') and e.stderr:
                error_msg += f"\nStderr: {e.stderr}"
            print(f"Task #{task_id} failed: {error_msg}")
            
            supabase.table('tasks').update({
                "status": "failed", 
                "done_at": datetime_now()
            }).eq("id", task_id).execute()

def datetime_now():
    from datetime import datetime
    return datetime.now().isoformat()

if __name__ == "__main__":
    main()
