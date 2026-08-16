"""Check remote server docker container status via SSH."""
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from tools.ssh_helper import connect_ssh

load_dotenv(ROOT_DIR / ".env")

ip = os.environ.get("RADAR_SERVER_IP", "193.242.125.76")
port = int(os.environ.get("RADAR_SERVER_PORT", "22"))
user = os.environ.get("RADAR_SERVER_USERNAME", "root")
pwd = os.environ.get("RADAR_SERVER_PASSWORD", "")

print(f"Connecting to {user}@{ip}:{port} ...")
try:
    ssh = connect_ssh(ip, port=port, username=user, password=pwd, timeout=10)
    stdin, stdout, stderr = ssh.exec_command("docker ps --filter name=iran_market_radar")
    output = stdout.read().decode("utf-8", errors="ignore")
    print("\n--- Remote Docker Containers ---")
    if output.strip():
        print(output)
    else:
        print("No active containers found matching 'iran_market_radar'.")
    ssh.close()
except Exception as e:
    print(f"\n❌ Error checking server status: {e}")
