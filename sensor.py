import logging
from homeassistant.components.sensor import SensorEntity
from homeassistant.const import EntityCategory
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import OpenWRTDataCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, config_entry, async_add_entities):
    data = config_entry.data
    ip = data.get("ip")
    config_type = data.get("config_type")

    coordinator = OpenWRTDataCoordinator(hass, ip, config_type)

    hass.data[DOMAIN][config_entry.entry_id] = {
        "coordinator": coordinator,
        "ip": ip,
        "config_type": config_type,
    }

    entities = [
        StaticOpenWRTSensor(
            coordinator, ip, "IP Address", ip, EntityCategory.DIAGNOSTIC
        ),
        StaticOpenWRTSensor(
            coordinator, ip, "Config Type", config_type, EntityCategory.DIAGNOSTIC
        ),
        DynamicOpenWRTSensor(coordinator, ip, "Device Name", "hostname"),
        DynamicOpenWRTSensor(coordinator, ip, "Current OS Version", "os_version"),
        DynamicOpenWRTSensor(
            coordinator, ip, "Status", "status", device_class="connectivity"
        ),
        DynamicOpenWRTSensor(
            coordinator, ip, "Available OS Version", "available_os_version"
        ),
    ]

    async_add_entities(entities, update_before_add=True)


class StaticOpenWRTSensor(CoordinatorEntity, SensorEntity):
    def __init__(self, coordinator, ip, name, value, entity_category=None):
        super().__init__(coordinator)
        self._attr_name = f"{name} ({ip})"
        # self._attr_unique_id = f"{ip}_{name.lower().replace(' ', '_')}"
        self._attr_unique_id = f"{name.lower().replace(' ', '_')}_{ip}"
        self._attr_native_value = value
        self._attr_entity_category = entity_category

    @property
    def should_poll(self):
        return False


class DynamicOpenWRTSensor(CoordinatorEntity, SensorEntity):
    def __init__(self, coordinator, ip, name, key, device_class=None):
        super().__init__(coordinator)
        self._attr_name = f"{name} ({ip})"
        self._attr_unique_id = f"{ip}_{name.lower().replace(' ', '_')}"
        self._key = key
        self._attr_device_class = device_class

    @property
    def native_value(self):
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.get(self._key)

    @property
    def available(self):
        return self.coordinator.last_update_success

