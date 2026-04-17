import os
import subprocess
import time
import sys
from datetime import datetime

# Configure Paths
BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
TOKEN_FILE = os.path.join(BACKEND_DIR, "fyers_token.txt")

def run_script(script_name, args=None):
    script_path = os.path.join(BACKEND_DIR, script_name)
    if not os.path.exists(script_path):
        print(f"❌ Script not found: {script_name}")
        return False
    
    cmd = [sys.executable, script_path]
    if args: cmd.extend(args)
    
    print(f"🚀 Running {script_name}...")
    try:
        # Using subprocess.run to wait for completion
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print(f"✅ {script_name} completed successfully.")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Error running {script_name}: {e}")
        print(e.output)
        return False

def check_fyers_token():
    if not os.path.exists(TOKEN_FILE):
        return False
    
    # Check if token is "fresh" (created/modified today)
    mtime = datetime.fromtimestamp(os.path.getmtime(TOKEN_FILE)).date()
    if mtime < datetime.now().date():
        print("⚠️ Fyers token might be stale (from a previous day).")
        # We try to use it anyway, but notify user
    return True

def master_automation():
    print("============================================================")
    print("🌟 VCP DASHBOARD MASTER AUTOMATION SYNC")
    print(f"⏰ Start Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("============================================================\n")

    # 1. Maintenance
    print("[1/4] Running System Maintenance...")
    run_script("master_maintenance.py")

    # 2. Data Refresh (India)
    print("\n[2/4] Refreshing Market Data...")
    if check_fyers_token():
        print("📡 Fyers Token detected. Starting high-quality Indian data refresh...")
        # Reduce workers to 2 to avoid 429 errors from Fyers
        run_script("refresh_india.py")
    else:
        print("⏭️ Skipping Fyers refresh (No token found). Dashboard will use existing data.")

    # 3. ML Intelligence Update
    print("\n[3/4] Updating ML Models with fresh data...")
    # This will build dataset and train models
    run_script("build_and_train.py")

    # 4. Generate Top Picks
    print("\n[4/4] Generating final Top Picks for the day...")
    run_script("vcp_picks.py")

    # Final Check
    print("\n🔍 Verifying Output Integrity...")
    cache_dir = os.path.join(BACKEND_DIR, "outputs", "scan_cache")
    today_str = datetime.now().strftime("%Y-%m-%d")
    in_cache = os.path.join(cache_dir, f"IN_{today_str}.pkl")
    
    if os.path.exists(in_cache):
        size = os.path.getsize(in_cache) / 1024
        print(f"✅ Cache found: {in_cache} ({size:.1f} KB)")
    else:
        print("⚠️ Warning: Today's scan result was not generated. You may need to refresh in the UI.")

    print("\n============================================================")
    print("🏁 FULL SYNC COMPLETE!")
    print("Navigate to the Dashboard to see your verified picks.")
    print("============================================================\n")

if __name__ == "__main__":
    master_automation()
