import logging
from datetime import timedelta
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady

from .ssh_client import get_hostname, get_os_version, test_ssh_connection
from .toh_parser import TOH
from .const import CONFIG_TYPES_PATH, KEY_PATH

import yaml

_LOGGER = logging.getLogger(__name__)
SCAN_INTERVAL = timedelta(minutes=10)


class OpenWRTDataCoordinator(DataUpdateCoordinator):
    def __init__(self, hass: HomeAssistant, ip: str, config_type: str):
        super().__init__(
            hass, _LOGGER, name="OpenWRT Updater", update_interval=SCAN_INTERVAL
        )
        self.ip = ip
        self.config_type = config_type
        self.toh = TOH(hass)

        # Load config_types.yaml
        self._config_types = self._load_config_types()
        self.ssh_key_path = hass.config.path(KEY_PATH)

    def _load_config_types(self):
        try:
            with open(self.hass.config.path(CONFIG_TYPES_PATH), "r") as f:
                return yaml.safe_load(f)
        except Exception as e:
            _LOGGER.error("Failed to load config_types.yaml: %s", e)
            return {}

    async def _async_update_data(self):
        try:
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
            openwrt_devid = self._config_types.get(self.config_type, {}).get(
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
            }

