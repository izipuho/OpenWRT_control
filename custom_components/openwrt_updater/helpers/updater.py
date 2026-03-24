"""Firmware upgrade workflows for OpenWRT devices."""

import logging
import re

from asyncssh import scp

from homeassistant.core import HomeAssistant

from .asu_client import ASUClient
from .const import DOMAIN
from .ssh_client import OpenWRTSSH

_LOGGER = logging.getLogger(__name__)


class OpenWRTUpdater:
    """Run firmware upgrade actions for a specific device."""

    def __init__(self, hass: HomeAssistant, config_entry_id, ip: str) -> None:
        """Initialize updater state for one device."""
        self.ip = ip
        self.config = hass.data[DOMAIN].get("config", {})
        data = hass.data[DOMAIN][config_entry_id].get(self.ip, {})
        coordinator = data["coordinator"].data
        # merge all dicts
        self.data = {
            **data,
            **coordinator,
            **hass.data[DOMAIN][config_entry_id].get("data", {}),
        }

        builder_location = re.fullmatch(
            r"([^@]+)@([^:]+):(.+)", self.config["builder_location"]
        )
        if not builder_location:
            raise ValueError(
                f"Invalid builder_location: {self.config['builder_location']!r}, expected format 'user@host:/dir'"
            )
        self.master_username, self.master_host, self.builder_dir = (
            builder_location.groups()
        )

        self.key_path = self.config["ssh_key_path"]
        self.place_name = self.data["place_name"]
        self.is_simple = bool(self.data["simple_update"])
        self.is_force = bool(self.data["force_update"])
        self.available_os_version = self.data["available_os_version"]
        self.snapshot_url = self.data["snapshot_url"]
        self._sanitized_filename = f"{self._sanitize(self.data['target'])}-{self._sanitize(self.data['board_name'])}-sysupgrade.bin"

    def _sysupgrade_command(self, firmware_file: str) -> str:
        """Compose sysupgrade command."""
        return (
            # f"/sbin/sysupgrade -T -v /tmp/{firmware_file} >/tmp/sysupgrade.log 2>&1 &"
            f"/sbin/sysupgrade -v /tmp/{firmware_file} >/tmp/sysupgrade.log 2>&1"
            # f"sysupgrade -v /tmp/{firmware_file}"
        )

    def _sanitize(self, s: str):
        """Normalize a string for use in a safe firmware filename."""
        return re.sub(
            r"-{2,}",
            "-",
            re.sub(
                r"[^a-z0-9._-]+",
                "-",
                s.strip().lower().replace("/", "-").replace(",", "-"),
            ),
        ).strip("-")

    @staticmethod
    def _status_from_output(output) -> tuple[bool, int | None, int | None]:
        """Convert command output to success/exit status/return code triple."""
        if output is None:
            return False, None, None

        exit_status = getattr(output, "exit_status", None)
        return_code = getattr(output, "return_code", None)
        success = exit_status in (0, None) and return_code in (0, None)
        return success, exit_status, return_code

    @staticmethod
    def _build_result(
        method: str,
        success: bool,
        *,
        message=None,
        exit_status: int | None = None,
        return_code: int | None = None,
        cached=None,
        raw=None,
    ) -> dict:
        """Build a normalized upgrade result payload."""
        return {
            "success": success,
            "method": method,
            "message": message,
            "exit_status": exit_status,
            "return_code": return_code,
            "cached": cached,
            "raw": raw,
        }

    async def cache_asu_firmware(self, firmware_url: str):
        """Cache the built firmware image on the master node."""
        async with OpenWRTSSH(
            ip=self.master_host, username=self.master_username, key_path=self.key_path
        ) as master:
            command = f"curl -L --fail --silent --show-error --create-dirs {firmware_url} --output {self.builder_dir}cache/{self.available_os_version}/{self._sanitized_filename}"
            await master.exec_command(command=command, timeout=900)

    async def sysupgrade(self, firmware_file: str):
        """Run sysupgrade with the given firmware file."""
        _LOGGER.debug("Trying to update %s with local file %s", self.ip, firmware_file)
        update_command = self._sysupgrade_command(firmware_file)
        async with OpenWRTSSH(self.ip, self.key_path) as client:
            _LOGGER.debug(
                "Start sysupgrade on %s with command %s", self.ip, update_command
            )
            return await client.exec_command(update_command, timeout=1800)

    async def simple_upgrade(self):
        """Run a direct snapshot-based upgrade from TOH data."""
        try:
            _LOGGER.debug("Trying to simple update %s", self.ip)
            _LOGGER.debug("Downloading %s", self.snapshot_url)
            update_command = f"curl -L --fail --silent --show-error {self.snapshot_url} --output /tmp/openwrt-{self.available_os_version}-simple.bin"
            if self.is_force:
                update_command = f"{update_command} && {self._sysupgrade_command(f'openwrt-{self.available_os_version}-simple.bin')}"
            async with OpenWRTSSH(self.ip, self.key_path) as client:
                output = await client.exec_command(update_command, timeout=900)
            _LOGGER.debug("Update result: %s", output)
        except Exception as err:
            _LOGGER.error("Failed to run simple update for %s: %s", self.ip, err)
            return self._build_result("simple", False, message=err)
        else:
            success, exit_status, return_code = self._status_from_output(output)
            return self._build_result(
                "simple",
                success,
                exit_status=exit_status,
                return_code=return_code,
                raw=output,
            )

    async def asu_upgrade(self):
        """Trigger ASU upgrade."""
        asu_client = None
        action = None
        command = None
        try:
            asu_client = self.data.get("asu_client")
            if not asu_client:
                raise RuntimeError(
                    "ASU update requires owut or auc on the router. Install it first and retry."
                )

            if asu_client == "owut":
                action = "upgrade" if self.is_force else "download"
                command = f"owut {action} -V {self.available_os_version}"
            elif asu_client == "auc":
                action = "upgrade"
                if not self.is_force:
                    raise RuntimeError(
                        "Manual ASU download requires owut on the router. Install owut or enable immediate install."
                    )
                command = f"auc -y -B {self.available_os_version}"
            else:
                raise RuntimeError(f"Unsupported ASU client on router: {asu_client}")

            _LOGGER.debug(
                "Starting ASU on %s via %s (%s): %s",
                self.ip,
                asu_client,
                action,
                command,
            )
            async with OpenWRTSSH(self.ip, self.key_path) as client:
                output = await client.exec_command(command, timeout=1800)

        except Exception as err:
            _LOGGER.error(
                "Failed to run ASU upgrade for %s via %s (%s): %s",
                self.ip,
                asu_client,
                action,
                err,
            )
            return self._build_result("asu", False, message=err)
        else:
            success, exit_status, return_code = self._status_from_output(output)
            stdout = (getattr(output, "stdout", "") or "").strip()
            stderr = (getattr(output, "stderr", "") or "").strip()
            message = stdout or stderr or None
            raw = {
                "backend": asu_client,
                "action": action,
                "command": command,
                "stdout": stdout,
                "stderr": stderr,
                "output": output,
            }

            if success:
                _LOGGER.debug(
                    "ASU finished for %s via %s (%s)", self.ip, asu_client, action
                )
            else:
                _LOGGER.error(
                    "ASU failed for %s via %s (%s): %s",
                    self.ip,
                    asu_client,
                    action,
                    stderr or stdout or output,
                )

            return self._build_result(
                "asu",
                success,
                message=message,
                exit_status=exit_status,
                return_code=return_code,
                raw=raw,
            )

    async def _check_cache(self) -> tuple[str, bool]:
        """Check whether the expected firmware image is already cached."""
        async with OpenWRTSSH(
            ip=self.master_host, username=self.master_username, key_path=self.key_path
        ) as master:
            fw_file, cached = await master.check_cached_firmware(
                self.builder_dir, self.available_os_version, self._sanitized_filename
            )
        return fw_file, cached

    async def trigger_upgrade(self):
        """Trigger the selected upgrade path."""
        if self.is_simple:
            return await self.simple_upgrade()
        return await self.asu_upgrade()
