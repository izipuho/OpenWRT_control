import paramiko
from .const import SSH_KEY_PATH

def test_ssh_connection(ip):
    try:
        key = paramiko.Ed25519Key(filename=SSH_KEY_PATH)
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(ip, username="root", pkey=key, timeout=10)
        ssh.close()
        return True
    except Exception:
        return False

def get_device_info(ip):
    key = paramiko.Ed25519Key(filename=SSH_KEY_PATH)
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(ip, username="root", pkey=key, timeout=10)

    stdin, stdout, _ = ssh.exec_command("uname -n; cat /etc/openwrt_version")
    hostname = stdout.readline().strip()
    os_version = stdout.readline().strip()
    ssh.close()
    return hostname, os_version

