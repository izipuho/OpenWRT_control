from homeassistant.helpers.entity import Entity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from .device import Device

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities):
    config = entry.data
    device = Device(
        config["ip"],
        config["device_type"],
        config["os"],
        config.get("key_path", "/config/ssh/id_rsa")
    )
    async_add_entities([OpenWRTSensor(device)])

class OpenWRTSensor(Entity):
    def __init__(self, device):
        self._device = device
        self._state = None

    @property
    def name(self):
        return f"{self._device.device_type} ({self._device.ip})"

    @property
    def state(self):
        return self._state

    def update(self):
        self._state = self._device.get_state()
