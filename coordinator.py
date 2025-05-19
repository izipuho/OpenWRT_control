from datetime import timedelta
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from .ssh_client import get_device_info
from .const import DOMAIN
import logging

_LOGGER = logging.getLogger(__name__)

class OpenWRTDataUpdateCoordinator(DataUpdateCoordinator):
    def __init__(self, hass, entry):
        self.ip = entry.data["ip"]
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_{self.ip}",
            update_interval=timedelta(minutes=5),
        )

    async def _async_update_data(self):
        try:
            hostname, os_version = await self.hass.async_add_executor_job(get_device_info, self.ip)
            return {
                "hostname": hostname,
                "os_version": os_version,
                "online": True
            }
        except Exception:
            return {
                "hostname": None,
                "os_version": None,
                "online": False
            }

