"""Backup-first production deployment for the dedicated Iran Market Radar stack."""
from __future__ import annotations

import io
import os
import secrets
import shlex
import sys
import time
import zipfile
from pathlib import Path

from dotenv import dotenv_values, load_dotenv

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from tools.ssh_helper import connect_ssh


REMOTE_ROOT = "/opt/iran-market-radar"
REMOTE_RELEASES = f"{REMOTE_ROOT}/releases"
REMOTE_SHARED = f"{REMOTE_ROOT}/shared"
REMOTE_CURRENT = f"{REMOTE_ROOT}/current"
COMPOSE_PROJECT = "iran-market-radar-prod"
PUBLIC_HTTPS_PORT = 3742
WEB_UPSTREAM_PORT = 13742
NGINX_SITE = "/etc/nginx/sites-available/iran-market-radar"

EXCLUDE_DIRS = {
    ".git", ".next", ".pytest_cache", ".secrets", ".venv", "__pycache__",
    "backups", "graphify-out", "logs", "node_modules", "output", "venv",
}
EXCLUDE_FILES = {".env", ".env.local", ".env.production"}
EXCLUDE_SUFFIXES = {".db", ".dump", ".key", ".log", ".pem", ".pyc", ".sqlite", ".zip"}


def _run(ssh, command: str, label: str, *, timeout: int = 1800) -> str:
    print(f"[remote] {label}")
    _stdin, stdout, stderr = ssh.exec_command(command, timeout=timeout, get_pty=False)
    output = stdout.read().decode("utf-8", errors="replace")
    error = stderr.read().decode("utf-8", errors="replace")
    status = stdout.channel.recv_exit_status()
    if output.strip():
        print(output.rstrip())
    if status != 0:
        raise RuntimeError(f"{label} failed (exit {status}): {error.strip()}")
    return output


def _package_release(release_id: str) -> Path:
    archive = ROOT_DIR / f"iran_market_radar_{release_id}.zip"
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as bundle:
        for root, dirs, files in os.walk(ROOT_DIR):
            dirs[:] = [name for name in dirs if name not in EXCLUDE_DIRS]
            for name in files:
                if name in EXCLUDE_FILES or Path(name).suffix.lower() in EXCLUDE_SUFFIXES:
                    continue
                path = Path(root) / name
                if path == archive:
                    continue
                bundle.write(path, path.relative_to(ROOT_DIR))
    print(f"[local] release archive: {archive.name} ({archive.stat().st_size / 1024 / 1024:.1f} MiB)")
    return archive


def _production_env() -> str:
    local = dotenv_values(ROOT_DIR / ".env")
    admin_user = str(local.get("RADAR_ADMIN_USER") or "").strip()
    admin_password = str(local.get("RADAR_ADMIN_PASSWORD") or "").strip()
    if not admin_user or not admin_password:
        raise RuntimeError("RADAR_ADMIN_USER and RADAR_ADMIN_PASSWORD must exist in the local server handoff environment")

    postgres_password = secrets.token_hex(24)
    redis_password = secrets.token_hex(24)
    session_secret = secrets.token_hex(48)
    values = {
        "APP_ENV": "production",
        "APP_PORT": "8742",
        "WEB_PORT": str(WEB_UPSTREAM_PORT),
        "WEB_BIND_HOST": "127.0.0.1",
        "RADAR_POSTGRES_PORT": "5742",
        "RADAR_REDIS_PORT": "6742",
        "LOG_LEVEL": "INFO",
        "SESSION_SECRET": session_secret,
        "SESSION_TTL_MINUTES": "43200",
        "RADAR_ADMIN_USER": admin_user,
        "RADAR_ADMIN_PASSWORD": admin_password,
        "COOKIE_SECURE": "true",
        "CORS_ORIGINS": f"https://193.242.125.76:{PUBLIC_HTTPS_PORT}",
        "INITIAL_PORTFOLIO_CASH_RIALS": "100000000000",
        "TRADING_MODE": "paper",
        "LIVE_TRADING_ENABLED": "false",
        "RISK_KILL_SWITCH_ARMED": "true",
        "AUTO_PAPER_TRADING_ENABLED": "true",
        "MARKET_DATA_MODE": "official",
        "MINIMUM_FUNDAMENTAL_SOURCES": "2",
        "BROKER_ADAPTER": "",
        "BROKER_CREDENTIALS": "",
        "DATA_HTTP_PROXY": "",
        "DATA_HTTP_TRUST_ENV": "false",
        "POSTGRES_PASSWORD": postgres_password,
        "REDIS_PASSWORD": redis_password,
        "DATABASE_URL": f"postgresql+asyncpg://radar_user:{postgres_password}@postgres:5432/iran_market_radar",
        "DATABASE_SYNC_URL": f"postgresql://radar_user:{postgres_password}@postgres:5432/iran_market_radar",
        "REDIS_URL": f"redis://:{redis_password}@redis:6379/0",
    }
    return "".join(f"{key}={value}\n" for key, value in values.items())


def _nginx_config() -> str:
    return f"""server {{
    listen {PUBLIC_HTTPS_PORT} ssl;
    listen [::]:{PUBLIC_HTTPS_PORT} ssl;
    server_name 193.242.125.76;

    ssl_certificate /etc/letsencrypt/live/193.242.125.76/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/193.242.125.76/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;

    location / {{
        proxy_pass http://127.0.0.1:{WEB_UPSTREAM_PORT};
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto https;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_read_timeout 120s;
        proxy_send_timeout 120s;
    }}
}}
"""


def _put_text(sftp, remote_path: str, text: str, mode: int) -> None:
    with sftp.file(remote_path, "w") as handle:
        handle.write(text)
    sftp.chmod(remote_path, mode)


def _put_archive_reliably(sftp, local_path: Path, remote_path: str) -> None:
    """Avoid Paramiko's pipelined put, which is brittle on this VPS/network path."""
    expected_size = local_path.stat().st_size
    with local_path.open("rb") as source, sftp.file(remote_path, "wb") as target:
        target.set_pipelined(False)
        while chunk := source.read(32 * 1024):
            target.write(chunk)
            target.flush()
    actual_size = sftp.stat(remote_path).st_size
    if actual_size != expected_size:
        raise RuntimeError(f"release upload size mismatch: expected {expected_size}, received {actual_size}")


def deploy() -> None:
    load_dotenv(ROOT_DIR / ".env")
    host = os.environ.get("RADAR_SERVER_IP", "").strip()
    port = int(os.environ.get("RADAR_SERVER_PORT", "22"))
    username = os.environ.get("RADAR_SERVER_USERNAME", "root").strip()
    password = os.environ.get("RADAR_SERVER_PASSWORD", "").strip()
    if host != "193.242.125.76":
        raise RuntimeError("Production host must be the explicitly authorized 193.242.125.76")

    release_id = time.strftime("%Y%m%d-%H%M%S")
    remote_release = f"{REMOTE_RELEASES}/{release_id}"
    archive = _package_release(release_id)
    ssh = connect_ssh(host, port=port, username=username, password=password, timeout=20)
    if ssh.get_transport() is not None:
        ssh.get_transport().set_keepalive(10)
    try:
        _run(
            ssh,
            f"mkdir -p {shlex.quote(REMOTE_RELEASES)} {shlex.quote(REMOTE_SHARED)}/backups {shlex.quote(remote_release)}",
            "create isolated production directories",
        )
        _run(
            ssh,
            "if ss -lnt | grep -q ':3742 ' && [ ! -L /etc/nginx/sites-enabled/iran-market-radar ]; then echo 'public port 3742 is already occupied'; exit 20; fi; "
            "if ss -lnt | grep -q ':13742 ' && [ ! -L /opt/iran-market-radar/current ]; then echo 'upstream port 13742 is occupied'; exit 21; fi; true",
            "verify dedicated ports do not conflict",
        )

        # Back up the existing paper ledger before any rebuild. First deploy has no container.
        _run(
            ssh,
            f"if docker ps --format '{{{{.Names}}}}' | grep -qx iran_market_radar_postgres; then "
            f"docker exec iran_market_radar_postgres pg_dump -U radar_user iran_market_radar | gzip -c > {REMOTE_SHARED}/backups/db-{release_id}.sql.gz; "
            f"test -s {REMOTE_SHARED}/backups/db-{release_id}.sql.gz; fi; "
            f"if [ -f {REMOTE_SHARED}/.env ]; then cp -a {REMOTE_SHARED}/.env {REMOTE_SHARED}/backups/env-{release_id}; chmod 600 {REMOTE_SHARED}/backups/env-{release_id}; fi",
            "backup current database and server-only environment",
        )

        sftp = ssh.open_sftp()
        try:
            remote_archive = f"{remote_release}/release.zip"
            print("[remote] upload release archive")
            _put_archive_reliably(sftp, archive, remote_archive)
            try:
                sftp.stat(f"{REMOTE_SHARED}/.env")
            except FileNotFoundError:
                _put_text(sftp, f"{REMOTE_SHARED}/.env", _production_env(), 0o600)
                print("[remote] created server-only production environment")
            _put_text(sftp, NGINX_SITE, _nginx_config(), 0o644)
        finally:
            sftp.close()

        _run(
            ssh,
            f"cd {shlex.quote(remote_release)} && unzip -q release.zip && rm -f release.zip && "
            f"ln -s {REMOTE_SHARED}/.env .env",
            "extract release and attach server-only environment",
        )
        compose = (
            f"docker compose --env-file {REMOTE_SHARED}/.env -p {COMPOSE_PROJECT} "
            f"-f {remote_release}/docker-compose.yml"
        )
        _run(ssh, f"{compose} build", "build production images")
        _run(ssh, f"{compose} up -d --remove-orphans", "start isolated production stack")
        _run(
            ssh,
            f"{compose} exec -T api python tools/start_paper_campaign.py",
            "ensure the auditable 10-billion-toman paper campaign",
        )
        _run(
            ssh,
            f"ln -sfn {shlex.quote(remote_release)} {REMOTE_CURRENT}.next && mv -Tf {REMOTE_CURRENT}.next {REMOTE_CURRENT}; "
            f"ln -sfn {NGINX_SITE} /etc/nginx/sites-enabled/iran-market-radar; nginx -t; systemctl reload nginx; "
            f"if command -v ufw >/dev/null 2>&1 && ufw status | grep -q '^Status: active'; then ufw allow {PUBLIC_HTTPS_PORT}/tcp >/dev/null; fi",
            "publish HTTPS port 3742 without changing other sites",
        )
        _run(
            ssh,
            f"for i in $(seq 1 30); do curl -kfsS --max-time 5 https://127.0.0.1:{PUBLIC_HTTPS_PORT}/api/v1/health >/tmp/radar-health.json && break; sleep 2; done; "
            f"test -s /tmp/radar-health.json; python3 -c 'import json; d=json.load(open(\"/tmp/radar-health.json\")); assert d.get(\"status\") in (\"ok\",\"healthy\",\"degraded\")'; "
            f"curl -kfsS --max-time 10 'https://127.0.0.1:{PUBLIC_HTTPS_PORT}/api/v1/market/reference-symbols?per_page=1' >/tmp/radar-reference.json; "
            f"docker compose --env-file {REMOTE_SHARED}/.env -p {COMPOSE_PROJECT} -f {remote_release}/docker-compose.yml ps",
            "verify public health, market endpoint, and containers",
            timeout=180,
        )
        print(f"PRODUCTION_URL=https://{host}:{PUBLIC_HTTPS_PORT}")
        print(f"RELEASE={release_id}")
    finally:
        ssh.close()
        archive.unlink(missing_ok=True)


if __name__ == "__main__":
    deploy()
