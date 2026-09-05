"""SSH Connection and Authentication Utilities for Server Deployment."""
from __future__ import annotations
import getpass
import os
import sys
import time
import paramiko


def connect_ssh(
    host: str,
    *,
    port: int = 22,
    username: str = "root",
    password: str = "",
    timeout: int = 20,
    retries: int = 2,
    retry_delay: float = 3.0,
) -> paramiko.SSHClient:
    """
    Connects to the remote Linux server using SSH keys or password fallback.
    """
    ssh = paramiko.SSHClient()
    ssh.load_system_host_keys()
    known_hosts = os.environ.get("RADAR_KNOWN_HOSTS_FILE", "").strip()
    if known_hosts:
        ssh.load_host_keys(known_hosts)
    ssh.set_missing_host_key_policy(paramiko.RejectPolicy())

    effective_password = password or os.environ.get("RADAR_SERVER_PASSWORD", "").strip() or None

    for attempt in range(retries):
        try:
            ssh.connect(
                host,
                port=port,
                username=username,
                password=effective_password,
                timeout=timeout,
                allow_agent=True,
                look_for_keys=True,
            )
            return ssh
        except paramiko.AuthenticationException:
            if attempt == retries - 1 and not effective_password:
                # Prompt user for password
                print(f"\n[SSH AUTH] Key authentication rejected for {username}@{host}.")
                prompt_pass = getpass.getpass(f"Enter SSH Password for {username}@{host}: ")
                if prompt_pass:
                    ssh.connect(
                        host,
                        port=port,
                        username=username,
                        password=prompt_pass,
                        timeout=timeout,
                        allow_agent=False,
                        look_for_keys=False,
                    )
                    return ssh
            raise
        except Exception as e:
            if attempt < retries - 1:
                time.sleep(retry_delay)
            else:
                ssh.close()
                raise
    return ssh
