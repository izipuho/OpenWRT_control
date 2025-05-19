import paramiko
import os

KEY_PATH = "/config/ssh_keys/id_ed25519"

def _connect_ssh(ip):
    key = paramiko.Ed25519Key.from_private_key_file(KEY_PATH)
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(ip, username="root", pkey=key, timeout=5)
    return client

def test_ssh_connection(ip):
    try:
        client = _connect_ssh(ip)
        client.close()
        return True
    except Exception as e:
        print(f"SSH test failed: {e}")
        return False

def get_device_name(ip):
    try:
        client = _connect_ssh(ip)
        stdin, stdout, stderr = client.exec_command("uci get system.@system[0].hostname")
        hostname = stdout.read().decode().strip()
        client.close()
        return hostname
    except Exception as e:
        print(f"Failed to get device name: {e}")
        return None

def get_os_version(ip):
    try:
        client = _connect_ssh(ip)
        stdin, stdout, stderr = client.exec_command("cat /etc/openwrt_version")
        version = stdout.read().decode().strip()
        client.close()
        return version
    except Exception as e:
        print(f"Failed to get OS version: {e}")
        return None

def is_device_online(ip):
    try:
        client = _connect_ssh(ip)
        client.close()
        return True
    except Exception:
        return False

