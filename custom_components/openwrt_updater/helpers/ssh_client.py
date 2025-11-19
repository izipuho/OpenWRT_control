"""SSH utils."""

import asyncio
import json
import logging
from pathlib import Path
import shlex

import asyncssh

_LOGGER = logging.getLogger(__name__)
logging.getLogger("asyncssh").setLevel(logging.WARNING)


class OpenWRTSSH:
    """Async SSH client wrapper around asyncssh with small convenience helpers.

    Usage:
        Call the high-level method:
        data = await OpenWRTSSHClient("10.0.0.1").async_get_device_info()
    """

    def __init__(
        self,
        ip: str,
        key_path: str,
        username: str = "root",
        connect_timeout: float = 5.0,
        command_timeout: float | None = 5.0,
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
        _LOGGER.debug(
            "Trying to connect to %s@%s",
            self.username,
            self.ip,
        )
        if self._conn is not None:
            return None

        key_file = Path(self.key_path)
        if key_file.exists():
            key_text = await asyncio.to_thread(Path(self.key_path).read_text)
            private_key = asyncssh.import_private_key(key_text)
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
                agent_forwarding=True,
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

    async def exec_command(self, command: str, timeout: float | None = None) -> str:
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
            effective_timeout = self.command_timeout if timeout is None else timeout
            result = await asyncio.wait_for(
                self._conn.run(f"sh -c {shlex.quote(command)}"), effective_timeout
            )
        except TimeoutError as err:
            _LOGGER.warning(
                "SSH command timed out on %s: %s, %s", self.ip, command, err
            )
            return None
        except Exception:
            _LOGGER.exception("Unexpected error running SSH command '%s'", command)
            return None
        else:
            if result.exit_status != 0:
                _LOGGER.error(
                    "Command \n\t%s\nrun failed: %s | %s",
                    command,
                    result.exit_status,
                    result.stderr,
                )
            return result

    async def scp(self, filename: str, target_path: str):
        """Copy local file over scp to remote server."""
        try:
            await asyncssh.scp(filename, (self._conn, target_path))
        except (asyncssh.SFTPError, asyncssh.ProcessError) as err:
            _LOGGER.error("SCP failed: remote refused transfer (%s)", err)
        except (TimeoutError, OSError, asyncssh.Error) as err:
            _LOGGER.error("SCP failed: connection or IO error (%s)", err)

    async def list_installed_packages(self) -> list[str]:
        """Return the list of installed package names on the device.

        Uses `opkg list-installed` and strips versions, keeping only names.
        Falls back to empty list if command fails.
        """
        cmd = "opkg list-installed | cut -d' ' -f1"
        res = await self.exec_command(cmd)
        packages = [line.strip() for line in res.stdout.splitlines() if line.strip()]
        _LOGGER.debug("Installed packages on %s: %d found", self.ip, len(packages))
        return packages

    async def find_downloaded_firmware(self) -> tuple[str | None, bool]:
        """Check for a downloaded firmware image; adjust glob/path to your flow.

        Returns:
            (firmware_file_path, firmware_downloaded_flag)

        """
        res = await self.exec_command("ls -1 /tmp/openwrt*.bin 2>/dev/null | head -n1")
        fw_file = _first_line(res.stdout)
        return (fw_file or None, bool(fw_file))

    async def check_cached_firmware(
        self, builder_dir: str, os: str, filename: str
    ) -> tuple[str | None, bool]:
        """Check for a cached firmware image on master node.

        Returns:
            (firmware_file_path, firmware_cached_flag)

        """
        command = f"{builder_dir}cache/{os}/{filename}"
        res = await self.exec_command(f"ls -1 {command} 2>/dev/null | head -n1")
        fw_file = _first_line(res.stdout)
        return (fw_file, bool(fw_file))

    async def read_board(self) -> dict:
        """Read board info."""
        cmd = "ubus call system board"
        res = await self.exec_command(cmd)
        board = json.loads(res.stdout)
        return (
            board["hostname"],
            board["release"]["version"],
            board["release"]["distribution"],
            board["release"]["target"],
            board["board_name"],
        )

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

    async def async_get_device_info(
        self,
    ) -> tuple[str | None, bool, bool | None, str | None, str | None, list[str], bool]:
        """Get device info: status, hostname, os version, firmware file presence."""
        try:
            async with self:
                status = True
                fw_file, fw_downloaded = await self.find_downloaded_firmware()
                (
                    hostname,
                    os_version,
                    distribution,
                    target,
                    board_name,
                ) = await self.read_board()
                pkgs = await self.list_installed_packages()
                has_asu = False
                if "owut" in pkgs or "auc" in pkgs:
                    has_asu = True
        except (TimeoutError, asyncssh.Error, OSError) as e:
            _LOGGER.debug("Device info over SSH fetch failed: %s", e)
            return None, False, None, None, None, None, None, None, [], False
        else:
            return (
                os_version,
                status,
                fw_downloaded,
                fw_file,
                hostname,
                distribution,
                target,
                board_name,
                pkgs,
                has_asu,
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
