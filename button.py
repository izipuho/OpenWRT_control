from homeassistant.components.button import ButtonEntity
from .ssh_client import run_update_script
from .const import DOMAIN

async def async_setup_entry(hass, config_entry, async_add_entities):
    ip = config_entry.data["ip"]
    async_add_entities([UpdateButton(ip)])

class UpdateButton(ButtonEntity):
    def __init__(self, ip):
        self._ip = ip
        self._attr_name = f"Force Update ({ip})"
        self._attr_unique_id = f"{ip}_force_update"

    async def async_press(self):
        await self.hass.async_add_executor_job(run_update_script)

