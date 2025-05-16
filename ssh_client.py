import paramiko
from .const import SSH_KEY_PATH

def test_ssh_connection(ip: str) -> bool:
    try:
        key = paramiko.Ed25519Key(filename=SSH_KEY_PATH)
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(
            hostname=ip,
            username="root",
            pkey=key,
            timeout=10
        )
        ssh.close()
        return True
    except Exception as e:
        print(f"SSH test failed: {e}")
        return False

