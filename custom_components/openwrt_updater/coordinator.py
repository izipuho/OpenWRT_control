"""Coordinator class for updating entites."""

from datetime import timedelta
import logging

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .config_loader import load_config_types
from .const import CONFIG_TYPES_PATH, KEY_PATH
from .ssh_client import get_hostname, get_os_version, test_ssh_connection
from .toh_parser import TOH

_LOGGER = logging.getLogger(__name__)
SCAN_INTERVAL = timedelta(minutes=10)


class OpenWRTDataCoordinator(DataUpdateCoordinator):
    """Coordinator class for updating device data."""

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry,
    ) -> None:
        """Initialize coorinator class."""
        super().__init__(
            hass, _LOGGER, name="OpenWRT Updater", update_interval=SCAN_INTERVAL
        )
        self.config_entry = config_entry
        self.toh = TOH(hass)

        self._config_types = {}
        self.ssh_key_path = hass.config.path(KEY_PATH)
        self.config_types_path = hass.config.path(CONFIG_TYPES_PATH)

    async def _async_update_data(self):
        devices = self.config_entry.data.get("devices", [])
        coordinator = {}
        for device in devices:
            ip = device["ip"]
            config_type = device["config_type"]
            try:
                config_types = await self.hass.async_add_executor_job(
                    load_config_types, self.config_types_path
                )
                hostname = await self.hass.async_add_executor_job(
                    get_hostname, ip, self.ssh_key_path
                )
                os_version = await self.hass.async_add_executor_job(
                    get_os_version, ip, self.ssh_key_path
                )
                status = await self.hass.async_add_executor_job(
                    test_ssh_connection, ip, self.ssh_key_path
                )

                # Get TOH data
                openwrt_devid = config_types.get(config_type, {}).get("openwrt-devid")
                await self.toh.fetch()
                self.toh.get_device_info(openwrt_devid)

            except Exception as err:
                raise ConfigEntryNotReady from err

            else:
                coordinator[ip] = {
                    "hostname": hostname,
                    "current_os_version": os_version,
                    "status": "online" if status else "offline",
                    "available_os_version": self.toh.version,
                    "snapshot_url": self.toh.snapshot_url,
                }
        _LOGGER.warning(coordinator)
        return coordinator
