"""SSH utils."""

import asyncio
import logging
from pathlib import Path

import asyncssh

_LOGGER = logging.getLogger(__name__)
logging.getLogger("asyncssh").setLevel(logging.WARNING)


class OpenWRTSSH:
    """Async SSH client wrapper around asyncssh with small convenience helpers.

    Usage:
        async with OpenWRTSSHClient("10.0.0.1") as cli:
            version = await cli.read_os_version()
            fw_file, fw_downloaded = await cli.find_downloaded_firmware()

    Or call the high-level method:
        data = await OpenWRTSSHClient("10.0.0.1").async_get_device_info()
    """

    def __init__(
        self,
        ip: str,
        key_path: str,
        username: str = "root",
        connect_timeout: float = 5.0,
        command_timeout: float = 5.0,
    ) -> None:
        """Initialize wrapper."""
        self.ip = ip
        self.key_path = key_path
        self.username = username
        self.connect_timeout = connect_timeout
        self.command_timeout = command_timeout
        self._conn: asyncssh.SSHClientConnection | None = None
        self.available = False

    async def __aenter__(self) -> "OpenWRTSSH":
        """Open SSH connection when entering async context."""
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        """Close SSH connection when leaving async context."""
        await self.close()

    async def connect(self) -> bool:
        """Connect handler."""
        _LOGGER.info(
            "Trying to connect to %s@%s with key %s",
            self.username,
            self.ip,
            self.key_path,
        )
        if self._conn is not None:
            return None

        key_file = Path(self.key_path)
        key_text = await asyncio.to_thread(Path(self.key_path).read_text)
        private_key = asyncssh.import_private_key(key_text)
        if key_file.exists():
            client_keys = [private_key]
        else:
            _LOGGER.warning(
                "SSH key not found at %s; attempting agent/defaults", self.key_path
            )
        try:
            self._conn = await asyncssh.connect(
                host=self.ip,
                username=self.username,
                client_keys=client_keys,
                known_hosts=None,
                connect_timeout=self.connect_timeout,
            )
        except (TimeoutError, asyncssh.Error, OSError) as exc:
            _LOGGER.warning("SSH connect to %s failed: %s", self.ip, exc)
            self._conn = None
            self.available = False
            raise
        except Exception as err:
            self.available = False
            _LOGGER.debug(
                "Unexpected error while connecting to SSH %s: %s", self.ip, err
            )
        else:
            _LOGGER.debug("Successfully connected to %s@%s", self.username, self.ip)
            self.available = True
        return self.available

    async def exec_command(self, command: str, timeout: float = None) -> str:
        """Run a remote command with a hard timeout; never raises on non-zero exit.

        Returns:
            asyncssh.SSHCompletedProcess with attributes: stdout, stderr, returncode.

        """
        if self._conn is None:
            await self.connect()

        assert self._conn is not None

        if not self.available:
            _LOGGER.debug("SSH client not available, skipping command: %s", command)
            return None

        try:
            _LOGGER.debug("Executing SSH command on %s | %s", self.ip, command)
            result = await asyncio.wait_for(
                self._conn.run(command), timeout or self.command_timeout
            )
        except TimeoutError as err:
            _LOGGER.warning(
                "SSH command timed out on %s: %s, %s", self.ip, command, err
            )
            return None
        except Exception as err:
            _LOGGER.exception(
                "Unexpected error running SSH command '%s': %s", command, err
            )
            return None
        else:
            return result

    async def read_os_version(self) -> str | None:
        """Read OS version."""
        os_version_command = (
            "cat /etc/openwrt_release | grep -oP \"(?<=RELEASE=\\').*?(?=\\')\""
        )
        res = await self.exec_command(os_version_command)
        return _first_line(res.stdout)

    async def find_downloaded_firmware(self) -> tuple[str | None, bool]:
        """Check for a downloaded firmware image; adjust glob/path to your flow.

        Returns:
            (firmware_file_path, firmware_downloaded_flag)

        """
        res = await self.exec_command(
            'sh -c "ls -1 /tmp/openwrt*.bin 2>/dev/null | head -n1"'
        )
        fw_file = _first_line(res.stdout)
        return (fw_file or None, bool(fw_file))

    async def read_hostname(self) -> str | None:
        """Read device hostname with tolerant fallbacks for OpenWRT."""
        cmd = (
            'sh -c "'
            "uci -q get system.@system[0].hostname || "
            "cat /proc/sys/kernel/hostname || "
            'hostname"'
        )
        res = await self.exec_command(cmd)
        return _first_line(res.stdout)

    async def close(self) -> None:
        """Close the SSH connection."""
        if self._conn is not None:
            try:
                self._conn.close()
                await self._conn.wait_closed()
            except Exception:
                _LOGGER.exception("Error closing SSH connection to %s", self.ip)
            finally:
                self._conn = None

    async def async_get_device_state(
        self,
    ) -> tuple[str | None, bool, bool | None, str | None, str | None]:
        """Get device info: status, hostname, os version, firmware file presence."""
        try:
            async with self:
                status = True
                os_version = await self.read_os_version()
                hostname = await self.read_hostname()
                fw_file, fw_downloaded = await self.find_downloaded_firmware()
        except (TimeoutError, asyncssh.Error, OSError) as e:
            _LOGGER.error("Device info over SSH fetch failed: %s", e)
            return None, False, None, None, None
        else:
            return (
                os_version,
                status,
                fw_downloaded,
                fw_file,
                hostname,
            )


def _first_line(text: str) -> str:
    """Return the first non-empty line from text, or None."""
    if not text:
        return None
    for line in text.splitlines():
        s = line.strip()
        if s:
            return s
    return None
