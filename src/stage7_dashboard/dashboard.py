"""Stage 7: Interactive GLOF-RAS Dashboard

Launches the Streamlit application or can be executed directly.
Run:
    streamlit run dashboard/app.py
or:
    python src/stage7_dashboard/dashboard.py
"""

import os
import subprocess
import sys

def main():
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
    app_path = os.path.join(repo_root, "dashboard", "app.py")
    
    print(f"Starting GLOF-RAS Dashboard from {app_path}...")
    try:
        subprocess.run(["streamlit", "run", app_path], check=True)
    except FileNotFoundError:
        # Fallback to python -m streamlit
        subprocess.run([sys.executable, "-m", "streamlit", "run", app_path], check=True)

if __name__ == "__main__":
    main()

