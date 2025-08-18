"""Coordinator class for updating entites."""

from datetime import timedelta
import logging

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import DOMAIN
from .helpers import load_config_types
from .ssh_client import get_device_info
from .toh_parser import TOH

_LOGGER = logging.getLogger(__name__)
SCAN_INTERVAL = timedelta(minutes=10)


class OpenWRTDataCoordinator(DataUpdateCoordinator):
    """Coordinator class for updating device data."""

    def __init__(
        self,
        hass: HomeAssistant,
        ip: str,
        # config_type: str,
    ) -> None:
        """Initialize coorinator class."""
        super().__init__(
            hass, _LOGGER, name=f"OpenWRT Updater ({ip})", update_interval=SCAN_INTERVAL
        )
        self._ip = ip
        self.config_type = (
            self.config_entry.options.get("devices", {})
            .get(self._ip, {})
            .get("config_type", None)
        )
        self.toh = TOH(hass)

        self.ssh_key_path = hass.data.get(DOMAIN, {}).get("config", {}).get("ssh_key_path", "")
        if not self.ssh_key_path:
            _LOGGER.error("No SSH key path defined in configuration.yaml.")
        self.config_types_path = hass.data.get(DOMAIN, {}).get("config", {}).get("config_types_path", "")

    async def _async_update_data(self):
        coordinator = {}
        try:
            # Load config types from local YAML
            config_types = await self.hass.async_add_executor_job(
                load_config_types, self.config_types_path
            )
            # Get SSH-based info
            (
                firmware_file,
                firmware_downloaded,
                hostname,
                os_version,
                status,
            ) = await self.hass.async_add_executor_job(
                get_device_info, self._ip, self.ssh_key_path
            )

            # Get TOH data
            openwrt_devid = config_types.get(self.config_type, {}).get("openwrt-devid")
            await self.toh.fetch()
            self.toh.get_device_info(openwrt_devid)

        except Exception as err:
            raise ConfigEntryNotReady from err

        else:
            coordinator = {
                "hostname": hostname,
                "current_os_version": os_version,
                "status": status,
                "available_os_version": self.toh.version,
                "snapshot_url": self.toh.snapshot_url,
                "firmware_downloaded": firmware_downloaded,
                "firmware_file": firmware_file,
            }
        _LOGGER.debug("Coordinator data: %s", coordinator)
        # Save coordinator data to hass.data
        self.hass.data[DOMAIN][self.config_entry.entry_id][self._ip].update(coordinator)
        _LOGGER.debug(
            "HAss data: %s", self.hass.data[DOMAIN][self.config_entry.entry_id]
        )
        return coordinator
