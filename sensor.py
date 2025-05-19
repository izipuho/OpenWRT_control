from homeassistant.helpers.entity import Entity
from .const import DOMAIN
from .ssh_client import get_hostname, get_os_version, test_ssh_connection

async def async_setup_entry(hass, config_entry, async_add_entities):
    data = config_entry.data
    ip = data.get("ip")
    config_type = data.get("config_type")

    sensors = [
        OpenWRTSensor(ip, "IP Address", lambda: ip),
        OpenWRTSensor(ip, "Config Type", lambda: config_type),
        OpenWRTSensor(ip, "Device Name", lambda: get_hostname(ip)),
        OpenWRTSensor(ip, "Current OS Version", lambda: get_os_version(ip)),
        OpenWRTSensor(ip, "Status", lambda: "online" if test_ssh_connection(ip) else "offline")
    ]
    async_add_entities(sensors)

class OpenWRTSensor(Entity):
    def __init__(self, ip, name, update_fn):
        self._ip = ip
        self._name = name
        self._update_fn = update_fn
        self._attr_name = f"{name} ({ip})"
        self._attr_unique_id = f"{ip}_{name.lower().replace(' ', '_')}"
        self._attr_native_value = None

    @property
    def should_poll(self):
        return True

    async def async_update(self):
        try:
            value = await self.hass.async_add_executor_job(self._update_fn)
            self._attr_native_value = value
        except Exception:
            self._attr_native_value = None
            self._attr_available = False
