"""Server Deployment Automation Script for Iran Market Radar."""
import os
import sys
import time
import zipfile
import paramiko
from pathlib import Path
from dotenv import load_dotenv

# Ensure root is on path
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from tools.ssh_helper import connect_ssh

load_dotenv(ROOT_DIR / ".env")

SERVER_IP = os.environ.get("RADAR_SERVER_IP", "193.242.125.76")
SERVER_PORT = int(os.environ.get("RADAR_SERVER_PORT", "22"))
USERNAME = os.environ.get("RADAR_SERVER_USERNAME", "root")
PASSWORD = os.environ.get("RADAR_SERVER_PASSWORD", "")
REMOTE_BASE_DIR = "/var/www/iran_market_radar"
ZIP_FILENAME = "iran_market_radar_deploy.zip"

EXCLUDE_NAMES = {
    ".git", "node_modules", "venv", ".venv", ".next", "__pycache__",
    ".pytest_cache", ".gemini", "backups", "logs", ".vscode", ".idea"
}
EXCLUDE_EXTS = {".zip", ".pyc", ".db", ".log", ".tar.gz"}


def create_deployment_zip() -> Path:
    """Packages project codebase into a deployment ZIP."""
    zip_path = ROOT_DIR / ZIP_FILENAME
    print(f"\n📦 Packaging codebase into {ZIP_FILENAME}...")

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(ROOT_DIR):
            dirs[:] = [d for d in dirs if d not in EXCLUDE_NAMES]
            for file in files:
                if any(file.endswith(ext) for ext in EXCLUDE_EXTS) or file == ZIP_FILENAME:
                    continue
                file_path = Path(root) / file
                arcname = file_path.relative_to(ROOT_DIR)
                zipf.write(file_path, arcname)

    size_mb = zip_path.stat().st_size / (1024 * 1024)
    print(f"✅ Archive created successfully ({size_mb:.2f} MB).")
    return zip_path


def run_remote_command(ssh: paramiko.SSHClient, command: str, description: str = ""):
    """Executes a command on the remote server and streams output."""
    if description:
        print(f"\n⚙️  [{description}] Executing: {command}")
    stdin, stdout, stderr = ssh.exec_command(command, get_pty=True)

    for line in iter(stdout.readline, ""):
        line_str = line.strip()
        if line_str:
            print(f"   {line_str}")

    exit_status = stdout.channel.recv_exit_status()
    if exit_status != 0:
        err = stderr.read().decode("utf-8", errors="ignore").strip()
        print(f"❌ Command failed with exit code {exit_status}: {err}")
        return False
    return True


def deploy_to_server():
    """Main deployment workflow."""
    print("=" * 70)
    print(f"  IRAN MARKET RADAR — REMOTE DOCKER DEPLOYMENT")
    print(f"  Target Server: {USERNAME}@{SERVER_IP}:{SERVER_PORT}")
    print(f"  Remote Directory: {REMOTE_BASE_DIR}")
    print("=" * 70)

    # 1. Create ZIP archive
    zip_path = create_deployment_zip()

    # 2. Connect via SSH
    print(f"\n🔌 Connecting to remote server {SERVER_IP}:{SERVER_PORT}...")
    try:
        ssh = connect_ssh(SERVER_IP, port=SERVER_PORT, username=USERNAME, password=PASSWORD)
        print("✅ SSH Connection established.")
    except Exception as e:
        print(f"❌ Failed to connect to server: {e}")
        return False

    try:
        # 3. Create remote directory
        run_remote_command(ssh, f"mkdir -p {REMOTE_BASE_DIR}", "Directory Setup")

        # 4. Upload archive via SFTP
        print(f"\n📤 Uploading {ZIP_FILENAME} via SFTP...")
        sftp = ssh.open_sftp()
        remote_zip = f"{REMOTE_BASE_DIR}/{ZIP_FILENAME}"

        def upload_progress(transferred, total):
            pct = (transferred / total) * 100
            print(f"\r   Uploading: {transferred / (1024*1024):.2f} MB / {total / (1024*1024):.2f} MB ({pct:.1f}%)", end="", flush=True)

        sftp.put(str(zip_path), remote_zip, callback=upload_progress)
        sftp.close()
        print("\n✅ Upload completed.")

        # 5. Extract and Deploy Docker Stack
        commands = [
            f"cd {REMOTE_BASE_DIR} && unzip -o {ZIP_FILENAME} && rm -f {ZIP_FILENAME}",
            f"cd {REMOTE_BASE_DIR} && docker compose down || true",
            f"cd {REMOTE_BASE_DIR} && docker compose build --no-cache",
            f"cd {REMOTE_BASE_DIR} && docker compose up -d",
            "docker ps --filter 'name=iran_market_radar'",
        ]

        for cmd in commands:
            success = run_remote_command(ssh, cmd)
            if not success:
                print("❌ Deployment stopped due to error.")
                return False

        print("\n" + "=" * 70)
        print("🎉 DEPLOYMENT SUCCESSFUL — IRAN MARKET RADAR IS ONLINE!")
        print(f"🌐 Frontend Web UI: http://{SERVER_IP}:3742")
        print(f"🚀 Backend API: http://{SERVER_IP}:8742/docs")
        print("🔐 Default Admin: admin / radar2026 (Persistent 30-Day Session)")
        print("=" * 70)
        return True

    finally:
        ssh.close()
        # Clean local zip
        if zip_path.exists():
            zip_path.unlink()


if __name__ == "__main__":
    success = deploy_to_server()
    sys.exit(0 if success else 1)
