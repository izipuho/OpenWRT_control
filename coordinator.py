from datetime import timedelta
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.core import HomeAssistant

from .device import get_device_info

class OpenWRTDataUpdateCoordinator(DataUpdateCoordinator):
    def __init__(self, hass: HomeAssistant, config: dict):
        self.ip = config["ip"]
        self.config_type = config["config_type"]
        update_interval = timedelta(minutes=5)

        super().__init__(
            hass,
            _LOGGER,
            name=f"OpenWRT Updater {self.ip}",
            update_interval=update_interval
        )

    async def _async_update_data(self):
        return await self.hass.async_add_executor_job(get_device_info, self.ip)

