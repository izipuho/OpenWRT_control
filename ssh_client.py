import paramiko
import os
import logging

_LOGGER = logging.getLogger(__name__)

def ssh_command(ip, command, key_path="/config/ssh/id_rsa"):
    try:
        if not os.path.exists(key_path):
            raise FileNotFoundError(f"SSH key not found: {key_path}")

        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(ip, username="root", key_filename=key_path, timeout=10)

        stdin, stdout, stderr = client.exec_command(command)
        output = stdout.read().decode().strip()
        client.close()
        return output
    except Exception as e:
        _LOGGER.error("SSH key-based connection failed to %s: %s", ip, e)
        return f"Error: {e}"
