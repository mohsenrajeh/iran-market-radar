"""Rotate local Iran Market Radar secrets without disclosing them to process output."""
from __future__ import annotations

import os
import re
import secrets
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
ENV_PATH = ROOT / ".env"


def _read_env() -> tuple[list[str], dict[str, str]]:
    lines = ENV_PATH.read_text(encoding="utf-8").splitlines()
    values: dict[str, str] = {}
    for line in lines:
        if line.strip() and not line.lstrip().startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            values[key.strip()] = value
    return lines, values


def _replace_values(lines: list[str], replacements: dict[str, str]) -> str:
    pending = dict(replacements)
    output: list[str] = []
    for line in lines:
        if line.strip() and not line.lstrip().startswith("#") and "=" in line:
            key = line.split("=", 1)[0].strip()
            if key in pending:
                output.append(f"{key}={pending.pop(key)}")
                continue
        output.append(line)
    if pending:
        output.extend(["", "# Generated local-only secrets"])
        output.extend(f"{key}={value}" for key, value in pending.items())
    return "\n".join(output) + "\n"


def main() -> None:
    if not ENV_PATH.exists():
        raise SystemExit(".env does not exist; copy .env.example and configure it first.")

    lines, current = _read_env()
    db_user = current.get("POSTGRES_USER", "radar_user")
    db_name = current.get("POSTGRES_DB", "iran_market_radar")
    identifier = re.compile(r"^[A-Za-z_][A-Za-z0-9_]{0,62}$")
    if not identifier.fullmatch(db_user) or not identifier.fullmatch(db_name):
        raise SystemExit("Unsafe PostgreSQL identifier in local .env; rotation aborted.")
    db_password = secrets.token_hex(24)
    redis_password = secrets.token_hex(24)
    session_secret = secrets.token_urlsafe(48)
    admin_password = secrets.token_urlsafe(24)

    alter_sql = f"ALTER USER {db_user} WITH PASSWORD '{db_password}';"
    subprocess.run(
        [
            "docker", "exec", "iran_market_radar_postgres", "psql",
            "-v", "ON_ERROR_STOP=1", "-U", db_user, "-d", db_name,
            "-c", alter_sql,
        ],
        cwd=ROOT,
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        text=True,
    )

    replacements = {
        "SESSION_SECRET": session_secret,
        "SESSION_TTL_MINUTES": current.get("SESSION_TTL_MINUTES", "720"),
        "RADAR_ADMIN_PASSWORD": admin_password,
        "COOKIE_SECURE": current.get("COOKIE_SECURE", "false"),
        "CORS_ORIGINS": current.get("CORS_ORIGINS", "http://127.0.0.1:3742,http://localhost:3742"),
        "POSTGRES_PASSWORD": db_password,
        "REDIS_PASSWORD": redis_password,
        "DATABASE_URL": f"postgresql+asyncpg://{db_user}:{db_password}@postgres:5432/{db_name}",
        "DATABASE_SYNC_URL": f"postgresql://{db_user}:{db_password}@postgres:5432/{db_name}",
        "REDIS_URL": f"redis://:{redis_password}@redis:6379/0",
        "MARKET_DATA_MODE": current.get("MARKET_DATA_MODE", "official"),
        "AUTO_PAPER_TRADING_ENABLED": current.get("AUTO_PAPER_TRADING_ENABLED", "false"),
    }
    temp_path = ENV_PATH.with_suffix(".env.rotating")
    temp_path.write_text(_replace_values(lines, replacements), encoding="utf-8")
    os.replace(temp_path, ENV_PATH)
    print("Local database, Redis, session, and administrator secrets rotated successfully.")
    print("The new administrator password is stored only in the ignored local .env file.")


if __name__ == "__main__":
    main()
