import paramiko
import logging

_LOGGER = logging.getLogger(__name__)


def _connect_ssh(ip, key_path):
    key = paramiko.Ed25519Key.from_private_key_file(key_path)
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(ip, username="root", pkey=key, timeout=5)
    return client


def test_ssh_connection(ip, key_path):
    try:
        client = _connect_ssh(ip, key_path)
        client.close()
        return True
    except Exception as e:
        _LOGGER.error("SSH test failed: %s", e)
        return False


def get_hostname(ip, key_path):
    try:
        client = _connect_ssh(ip, key_path)
        stdin, stdout, stderr = client.exec_command("cat /proc/sys/kernel/hostname")
        name = stdout.read().decode().strip()
        client.close()
        return name
    except Exception as e:
        _LOGGER.error("SSH hostname fetch failed: %s", e)
        return None


def get_os_version(ip, key_path):
    try:
        client = _connect_ssh(ip, key_path)
        stdin, stdout, stderr = client.exec_command(
            "cat /etc/openwrt_release | grep -oP \"(?<=RELEASE=\\').*?(?=\\')\""
        )
        version = stdout.read().decode().strip()
        client.close()
        return version
    except Exception as e:
        _LOGGER.error("SSH OS version fetch failed: %s", e)
        return None


def run_update_script():
    try:
        client = _connect_ssh("10.8.25.20")
        stdin, stdout, stderr = client.exec_command("uname")
        output = stdout.read().decode().strip()
        client.close()
        return output
    except Exception as e:
        _LOGGER.error("Failed to run update script: %s", e)
        return None

