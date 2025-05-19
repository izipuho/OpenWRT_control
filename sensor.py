from homeassistant.helpers.entity import Entity
from .const import DOMAIN

async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([
        OpenWRTSensor(coordinator, "IP", entry.data["ip"]),
        OpenWRTSensor(coordinator, "Config Type", entry.data["config_type"]),
        OpenWRTSensor(coordinator, "Current OS", coordinator.data.get("os_version")),
        OpenWRTSensor(coordinator, "Status", "Online" if coordinator.data.get("online") else "Offline"),
    ])

class OpenWRTSensor(Entity):
    def __init__(self, coordinator, name, value):
        self._attr_name = name
        self._state = value

    @property
    def state(self):
        return self._state

