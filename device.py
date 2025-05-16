import paramiko
from .const import SSH_KEY_PATH

def get_device_info(ip):
    try:
        key = paramiko.Ed25519Key(filename=SSH_KEY_PATH)
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(ip, username="root", pkey=key, timeout=10)

        stdin, stdout, _ = ssh.exec_command("uname -n && cat /etc/openwrt_version")
        lines = stdout.read().decode().splitlines()
        ssh.close()

        return {
            "hostname": lines[0],
            "os_version": lines[1],
            "online": True
        }
    except Exception as e:
        return {
            "hostname": "Unknown",
            "os_version": "Unavailable",
            "online": False
        }

