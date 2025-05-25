import logging
from datetime import timedelta
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady

from .ssh_client import get_hostname, get_os_version, test_ssh_connection
from .toh_parser import TOH
from .const import CONFIG_TYPES_PATH, KEY_PATH
from .config_loader import load_config_types

import yaml

_LOGGER = logging.getLogger(__name__)
SCAN_INTERVAL = timedelta(minutes=10)


class OpenWRTDataCoordinator(DataUpdateCoordinator):
    def __init__(self, hass: HomeAssistant, ip: str, config_type: str, is_simple: bool = True):
        super().__init__(
            hass, _LOGGER, name="OpenWRT Updater", update_interval=SCAN_INTERVAL
        )
        self.ip = ip
        self.config_type = config_type
        self.is_simple = is_simple
        self.toh = TOH(hass)

        self._config_types = {}
        self.ssh_key_path = hass.config.path(KEY_PATH)
        self.config_types_path = hass.config.path(CONFIG_TYPES_PATH)

    async def _async_update_data(self):
        try:
            config_types = await self.hass.async_add_executor_job(load_config_types, self.config_types_path)
            hostname = await self.hass.async_add_executor_job(
                get_hostname, self.ip, self.ssh_key_path
            )
            os_version = await self.hass.async_add_executor_job(
                get_os_version, self.ip, self.ssh_key_path
            )
            status = await self.hass.async_add_executor_job(
                test_ssh_connection, self.ip, self.ssh_key_path
            )

            # Get TOH data
            openwrt_devid = config_types.get(self.config_type, {}).get(
                "openwrt-devid"
            )
            await self.toh.fetch()
            self.toh.get_device_info(openwrt_devid)

        except Exception as err:
            raise ConfigEntryNotReady from err

        else:
            return {
                "hostname": hostname,
                "current_os_version": os_version,
                "status": "online" if status else "offline",
                "available_os_version": self.toh.version,
                "is_simple": self.is_simple
            }

