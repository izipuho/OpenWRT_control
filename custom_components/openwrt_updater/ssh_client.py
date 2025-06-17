"""SSH utils."""

import logging
import socket

import paramiko

_LOGGER = logging.getLogger(__name__)

class OpenWRTSSH:
    """OpenWRT updater ssh wrapper."""

    def __init__(self, ip: str, key_path: str, username: str = "root", timeout: float = 5.0):
        """Initialize wrapper."""
        self.ip = ip
        self.key_path = key_path
        self.username = username
        self.timeout = timeout
        self.client = paramiko.SSHClient()
        self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self.available = False

    def connect(self) -> bool:
        """Connect handler."""
        _LOGGER.info("Trying to connect to %s@%s with key %s", self.username, self.ip, self.key_path)
        key = paramiko.Ed25519Key.from_private_key_file(self.key_path)
        try:
            self.client.connect(hostname=self.ip, username=self.username, pkey=key, timeout=self.timeout, allow_agent=False)
        except paramiko.AuthenticationException:
            self.available = False
            _LOGGER.warning("SSH authentication failed for %s@%s", self.username, self.ip)
        except (paramiko.SSHException, socket.error) as err:
            self.available = False
            _LOGGER.debug("SSH connection error to %s - %s", self.ip, err)
        except Exception as err:
            self.available = False
            _LOGGER.debug("Unexpected error while connecting to SSH %s", self.ip)
        else:
            _LOGGER.debug("Successfully connected to %s@%s", self.username, self.ip)
            self.available = True
        return self.available

    def exec_command(self, command: str, timeout: float = None) -> str:
        """
        Run a command over SSH and return its output.
        Raises no exception if the client is unavailable; returns empty string instead.
        """
        if not self.available:
            _LOGGER.debug("SSH client not available, skipping command: %s", command)
            return None
        try:
            _LOGGER.debug("Executing SSH command on %s | %s", self.ip, command)
            stdin, stdout, stderr = self.client.exec_command(command, timeout=timeout)
            stdout_str = stdout.read().decode('utf-8').strip()
            err_str = stderr.read().decode('utf-8').strip()
            if err_str:
                _LOGGER.error("Error output from command '%s': %s", command, err_str)
        except socket.timeout:
            _LOGGER.warning("SSH command timed out on %s: %s", self.ip, command)
            return None
        except paramiko.SSHException as err:
            _LOGGER.error("SSH exception running command '%s': %s", command, err)
            return None
        except Exception as err:
            _LOGGER.exception("Unexpected error running SSH command '%s'", command)
            return None
        else:
            return stdout_str

    def close(self) -> None:
        """Close the SSH connection."""
        try:
            _LOGGER.debug("Closing SSH connection to %s", self.ip)
            self.client.close()
            self.available = False
        except Exception:
            _LOGGER.exception("Error closing SSH connection to %s", self.ip)


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
        client = OpenWRTSSH(ip, key_path)
        status = client.connect()
        firmware_file = (
            client.exec_command(firmware_file_command)
        )
        #if len(firmware_file.split()) > 1:
        #    firmware_file = False
        os_version = client.exec_command(os_version_command)
        hostname = client.exec_command(hostname_command)
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
            status,
        )
