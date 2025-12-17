"""Update function."""

import logging
import re

from asyncssh import scp

from homeassistant.core import HomeAssistant

from .asu_client import ASUClient
from ..presets.const import DOMAIN
from .ssh_client import OpenWRTSSH

_LOGGER = logging.getLogger(__name__)


class OpenWRTUpdater:
    """Updater class."""

    def __init__(self, hass: HomeAssistant, config_entry_id, ip: str) -> None:
        """Initialize OpenWRT Updater."""
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
        return re.sub(
            r"-{2,}",
            "-",
            re.sub(
                r"[^a-z0-9._-]+",
                "-",
                s.strip().lower().replace("/", "-").replace(",", "-"),
            ),
        ).strip("-")

    async def cache_asu_firmware(self, firmware_url: str):
        """Cache builded FW on master node."""
        async with OpenWRTSSH(
            ip=self.master_host, username=self.master_username, key_path=self.key_path
        ) as master:
            command = f"curl -L --fail --silent --show-error --create-dirs {firmware_url} --output {self.builder_dir}cache/{self.available_os_version}/{self._sanitized_filename}"
            await master.exec_command(command=command, timeout=900)

    async def sysupgrade(self, firmware_file: str):
        """Launch sysupgrade with given file."""
        _LOGGER.debug("Trying to update %s with local file %s", self.ip, firmware_file)
        update_command = self._sysupgrade_command(firmware_file)
        async with OpenWRTSSH(self.ip, self.key_path) as client:
            _LOGGER.debug(
                "Start sysupgrade on %s with command %s", self.ip, update_command
            )
            return await client.exec_command(update_command, timeout=1800)

    async def simple_upgrade(self):
        """Trigger simple update. Download snapshot from TOH."""
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
            return {
                "success": False,
                "method": "simple",
                "message": err,
                "exit_status": None,
                "return_code": None,
                "cached": None,
                "raw": None,
            }
        else:
            if output is None:
                exit_status = None
                return_code = None
                success = False
            else:
                exit_status = getattr(output, "exit_status", None)
                return_code = getattr(output, "return_code", None)
                success = True
            return {
                "success": success,
                "method": "simple",
                "message": None,
                "exit_status": exit_status,
                "return_code": return_code,
                "cached": None,
                "raw": output,
            }

    async def asu_upgrade(self):
        """Trigger ASU upgrade."""
        ASU_BASE_URL = self.config["asu_base_url"]
        try:
            fw_file, cached = await self._check_cache()

            sysupgrade_raw = None
            exit_status = None
            return_code = None
            success = True  # be optimistic

            if not cached:
                # Cache builded FW on master node
                asu_client = ASUClient(base_url=ASU_BASE_URL)
                target = self.data["target"]
                board_name = self.data["board_name"]
                req = await asu_client.build_request(
                    version=self.available_os_version,
                    target=target,
                    board_name=board_name,
                    packages=self.data["packages"],
                    client_name=f"OpenWRT {self.place_name} {self.ip}",
                )
                _LOGGER.debug("Build request: %s", req.get("request_hash"))
                bin_dir, file_name = await asu_client.poll_build_request(
                    request_hash=req.get("request_hash")
                )
                fw_url = f"{ASU_BASE_URL}store/{bin_dir}/{file_name}"
                _LOGGER.debug("Build URL: %s", fw_url)
                await self.cache_asu_firmware(firmware_url=fw_url)

            async with OpenWRTSSH(
                ip=self.master_host,
                username=self.master_username,
                key_path=self.key_path,
            ) as master:
                router = await master.connect_tunneled(
                    host=self.ip, key_path=self.key_path
                )
                try:
                    await scp(
                        (master.conn, fw_file),
                        (
                            router,
                            f"/tmp/openwrt-{self.available_os_version}-asu.bin",
                        ),
                        preserve=True,
                    )
                except Exception as e:
                    _LOGGER.error("SCP failed with %s", e)
                    success = False
                finally:
                    router.close()
                    await router.wait_closed()

            if success and self.is_force:
                sysupgrade_raw = await self.sysupgrade(
                    f"openwrt-{self.available_os_version}-asu.bin"
                )
                if sysupgrade_raw is None:
                    _LOGGER.error("Sysupgrade failed or timed out on %s", self.ip)
                    success = False
                else:
                    exit_status = getattr(sysupgrade_raw, "exit_status", None)
                    return_code = getattr(sysupgrade_raw, "return_code", None)
                    success = exit_status in (0, None) and return_code in (
                        0,
                        None,
                    )
                    if not success:
                        _LOGGER.error(
                            "Failed to sysupgrade %s: %s", self.ip, sysupgrade_raw
                        )

        except Exception as err:
            _LOGGER.error("Failed to run ASU upgrade for %s: %s", self.ip, err)
            return {
                "success": False,
                "method": "asu",
                "message": err,
                "exit_status": None,
                "return_code": None,
                "cached": None,
                "raw": None,
            }
        else:
            return {
                "success": success,
                "method": "asu",
                "message": None,
                "exit_status": exit_status,
                "return_code": return_code,
                "cached": None,
                "raw": sysupgrade_raw,
            }

    async def _check_cache(self) -> tuple[str, bool]:
        """Check cached build."""
        async with OpenWRTSSH(
            ip=self.master_host, username=self.master_username, key_path=self.key_path
        ) as master:
            fw_file, cached = await master.check_cached_firmware(
                self.builder_dir, self.available_os_version, self._sanitized_filename
            )
        return fw_file, cached

    async def trigger_upgrade(self):
        """Trigger upgrade. Wrapper."""
        if self.is_simple:
            return await self.simple_upgrade()
        return await self.asu_upgrade()
