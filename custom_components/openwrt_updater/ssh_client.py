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


def get_device_info(ip, key_path):
    """Get device info: status, hostname, os version, firmware file presence."""
    firmware_file_command = (
        "ls /tmp/*wrt*.bin 2>/dev/null"
    )
    os_version_command = (
        "cat /etc/openwrt_release | grep -oP \"(?<=RELEASE=\\').*?(?=\\')\""
    )
    hostname_command = "cat /proc/sys/kernel/hostname"
    try:
        client = _connect_ssh(ip, key_path)
        firmware_file = (
            client.exec_command(firmware_file_command)[1].read().decode().strip()
        )
        if len(firmware_file.split()) > 1:
            firmware_file = False
        os_version = client.exec_command(os_version_command)[1].read().decode().strip()
        hostname = client.exec_command(hostname_command)[1].read().decode().strip()
        client.close()
    except Exception as e:
        _LOGGER.error("Device info over SSH fetch failed: %s", e)
        return None, None, None, None, False
    else:
        return (
            firmware_file,
            True if firmware_file else False,
            hostname,
            os_version,
            True,
        )
