"""Coordinator class for updating entites."""

from datetime import timedelta
import logging

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .config_loader import load_config_types
from .const import CONFIG_TYPES_PATH, KEY_PATH
from .ssh_client import get_device_info
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
            _LOGGER.debug("Device: %s", device)
            ip = device["ip"]
            config_type = device["config_type"]
            try:
                config_types = await self.hass.async_add_executor_job(
                    load_config_types, self.config_types_path
                )
                (
                    firmware_downloaded,
                    hostname,
                    os_version,
                    status,
                ) = await self.hass.async_add_executor_job(
                    get_device_info, ip, self.ssh_key_path
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
                    # "status": "on" if status else "off",
                    "status": status,
                    "available_os_version": self.toh.version,
                    "snapshot_url": self.toh.snapshot_url,
                    # "firmware_downloaded": "on" if firmware_downloaded else "off",
                    "firmware_downloaded": firmware_downloaded,
                }
        _LOGGER.warning("Coordinator: %s", coordinator)
        return coordinator
