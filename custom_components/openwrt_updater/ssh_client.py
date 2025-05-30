"""SSH utils."""

import logging

import paramiko

_LOGGER = logging.getLogger(__name__)


def _connect_ssh(ip, key_path, username: str = "root"):
    """Connect handler."""
    _LOGGER.info("Trying to connect to %s@%s with key %s", username, ip, key_path)
    key = paramiko.Ed25519Key.from_private_key_file(key_path)
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(ip, username=username, pkey=key, timeout=5)
    return client


def test_ssh_connection(ip, key_path):
    """Test ssh connection."""
    try:
        client = _connect_ssh(ip, key_path)
        client.close()
    except Exception as e:
        _LOGGER.error("SSH test failed: %s", e)
        return False
    else:
        return True


def get_hostname(ip, key_path):
    """Return hostname pulled over ssh."""
    try:
        client = _connect_ssh(ip, key_path)
        stdin, stdout, stderr = client.exec_command("cat /proc/sys/kernel/hostname")
        name = stdout.read().decode().strip()
        client.close()
    except Exception as e:
        _LOGGER.error("SSH hostname fetch failed: %s, %s", ip, e)
        return None
    else:
        return name


def get_os_version(ip, key_path):
    """Return current OS version pulled over ssh."""
    try:
        client = _connect_ssh(ip, key_path)
        stdin, stdout, stderr = client.exec_command(
            "cat /etc/openwrt_release | grep -oP \"(?<=RELEASE=\\').*?(?=\\')\""
        )
        version = stdout.read().decode().strip()
        client.close()
    except Exception as e:
        _LOGGER.error("SSH OS version fetch failed: %s", e)
        return None
    else:
        return version
