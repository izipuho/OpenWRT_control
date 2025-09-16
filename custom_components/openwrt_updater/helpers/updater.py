"""Update function."""

import logging
import re
import shlex

from homeassistant.core import HomeAssistant

from .asu_client import ASUClient
from .const import DOMAIN
from .ssh_client import OpenWRTSSH

_LOGGER = logging.getLogger(__name__)


class OpenWRTUpdater:
    """Updater class."""

    def __init__(self, hass: HomeAssistant, config_entry_id, ip: str) -> None:
        """Initialize OpenWRT Updater."""
        self.ip = ip
        self.config = hass.data[DOMAIN].get("config", {})
        data = hass.data[DOMAIN][config_entry_id].get(self.ip, {})
        coordinator = data["coordinator"]
        # merge all dicts
        self.data = {
            **data,
            **coordinator.data,
            **hass.data[DOMAIN][config_entry_id].get("data", {}),
        }

        builder_location = re.fullmatch(
            r"([^@]+)@([^:]+):(.+)", self.config["builder_location"]
        )
        self.master_username, self.master_host, self.builder_dir = (
            builder_location.groups()
        )

        self.key_path = self.config["ssh_key_path"]
        self.place_name = self.data["place_name"]
        self.is_simple = bool(self.data["simple_update"])
        self.is_force = bool(self.data["force_update"])
        self.available_os_version = shlex.quote(self.data["available_os_version"])
        self.snapshot_url = shlex.quote(self.data["snapshot_url"])

    def _sysupgrade_command(self, firmware_file: str) -> str:
        """Compose sysupgrade command."""
        return f"nohup sysupgrade -v /tmp/{firmware_file} >/tmp/sysupgrade.log 2>&1 &"

    def _sanitize(self, s: str):
        return re.sub(
            r"-{2,}",
            "-",
            re.sub(
                r"[^a-z0-9._-]+",
                "-",
                s.strip().lower().replace("/", "-").replace(",", "-"),
            ),
        ).strip("-")

    async def cache_firmware(
        self, type: str, firmware_url: str, target: str, board_name: str
    ):
        """Cache builded FW on master node."""
        async with OpenWRTSSH(
            ip=self.master_host, username=self.master_username, key_path=self.key_path
        ) as master:
            filename = (
                f"{self._sanitize(target)}-{self._sanitize(board_name)}-sysupgrade.bin"
            )

            command = f"curl -L --fail --silent --show-error --create-dirs {firmware_url} --output {self.builder_dir}/cache/{self.available_os_version}/{type}/{filename}"
            await master.exec_command(command=command, timeout=900)
            return filename

    async def sysupgrade(self, firmware_file: str):
        """Launch sysupgrade with given file."""
        _LOGGER.debug(
            "Trying to update %s with local file %s", self.ip, self.firmware_file
        )
        update_command = f"sh -c '{self._sysupgrade_command(firmware_file)}'"
        async with OpenWRTSSH(self.ip, self.key_path) as client:
            return await client.exec_command(update_command, timeout=10)

    async def simple_upgrade(self):
        """Trigger simple update. Download snapshot from TOH."""
        try:
            _LOGGER.debug("Trying to simple update %s", self.ip)
            _LOGGER.debug("Downloading %s", self.snapshot_url)
            update_command = f"curl -L --fail --silent --show-error {self.snapshot_url} --output /tmp/openwrt-{self.available_os_version}-simple.bin"
            if self.is_force:
                update_command = f"sh -c '{update_command} && {self._sysupgrade_command(f'openwrt-{self.available_os_version}-simple.bin')}'"
            async with OpenWRTSSH(self.ip, self.key_path) as client:
                output = await client.exec_command(update_command, timeout=900)
            _LOGGER.debug("Update result: %s", output)
        except Exception:
            _LOGGER.error("Failed to run simple update for %s", self.ip)
            return None
        else:
            return output

    async def asu_upgrade(self):
        """Trigger ASU upgrade."""
        ASU_BASE_URL = self.config["asu_base_url"]
        try:
            async with ASUClient(base_url=ASU_BASE_URL) as client:
                req = await client.build_request(
                    version=self.available_os_version,
                    target=self.data["target"],
                    board_name=self.data["board_name"],
                    packages=self.data["packages"],
                    client_name=f"OpenWRT {self.place_name} {self.ip}",
                )
                _LOGGER.warning("Build request: %s", req.get("request_hash"))
                bin_dir, file_name = await client.poll_build_request(
                    request_hash=req.get("request_hash")
                )
                fw_url = f"{client.base_url}/store/{bin_dir}/{file_name}"
                _LOGGER.warning("Build URL: %s", fw_url)
                update_command = f"curl -L --fail --silent --show-error {fw_url} --output /tmp/openwrt-{self.available_os_version}-asu.bin"
                if self.is_force:
                    update_command = f"sh -c '{update_command} && {self._sysupgrade_command(f'openwrt-{self.available_os_version}-asu.bin')}'"
                async with OpenWRTSSH(self.ip, self.key_path) as client:
                    output = await client.exec_command(update_command, timeout=900)
        except Exception:
            _LOGGER.error("Failed to run simple update for %s", self.ip)
            return None
        else:
            return output

    async def custom_build_upgrade(self):
        """Trigger custom build on master node."""
        config_type = shlex.quote(self.data["config_type"])
        update_strategy = "install" if self.is_force else "copy"
        update_command = f"cd {self.builder_dir} && make C={config_type} HOST={self.ip} RELEASE={self.available_os_version} {update_strategy}"
        try:
            _LOGGER.debug("Trying to update %s with %s", self.ip, update_command)
            async with OpenWRTSSH(
                ip=self.master_host,
                key_path=self.key_path,
                username=self.master_username,
            ) as master:
                output = await master.exec_command(
                    f"sh -c '{update_command}'", timeout=1800
                )
            _LOGGER.debug("Update result: %s", output)
        except Exception:
            _LOGGER.error("Failed to run builder script on %s", self.ip)
            return None
        else:
            return output

    async def trigger_upgrade(self):
        """Trigger upgrade. Wrapper."""
        if self.is_simple:
            await self.simple_upgrade()
        else:
            ASU = self.config["use_asu"]
            if ASU:
                await self.asu_upgrade()
            else:
                await self.custom_build_upgrade()
