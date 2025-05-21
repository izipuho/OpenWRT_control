import logging

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.components.sensor import SensorEntity
from homeassistant.const import EntityCategory
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import OpenWRTDataCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, config_entry, async_add_entities):
    devices = config_entry.data.get("devices", [])

    entities = []
    for device in devices:
        ip = device["ip"]
        config_type = device["config_type"]

        coordinator = OpenWRTDataCoordinator(hass, ip, config_type)

        entities.extend(
            [
                OpenWRTSensor(
                    coordinator,
                    ip,
                    "IP Address",
                    static_value=ip,
                ),
                OpenWRTSensor(
                    coordinator,
                    ip,
                    "Config Type",
                    static_value=config_type,
                ),
                OpenWRTSensor(coordinator, ip, "Device Name", key="hostname"),
                # OpenWRTSensor(coordinator, ip, "Current OS Version", key="current_os_version"),
                # OpenWRTSensor(coordinator, ip, "Available OS Version", key="available_os_version"),
            ]
        )

    async_add_entities(entities, update_before_add=True)


class OpenWRTSensor(CoordinatorEntity, SensorEntity):
    def __init__(
        self,
        coordinator,
        ip: str,
        name: str,
        *,
        key=None,
        static_value=None,
        device_class=None,
        entity_category: EntityCategory = None,
    ):
        super().__init__(coordinator)
        self._ip = ip
        self._name = name
        self._key = key
        self._static_value = static_value
        self._attr_name = f"{name} ({ip})"
        self._attr_unique_id = f"{ip}_{name.lower().replace(' ', '_')}"
        self._attr_device_class = device_class
        self._attr_entity_category = entity_category

    @property
    def native_value(self):
        if self._key:
            return (
                self.coordinator.data.get(self._key) if self.coordinator.data else None
            )
        return self._static_value

    @property
    def available(self):
        return self.coordinator.last_update_success if self._key else True

    @property
    def should_poll(self):
        return False

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, self._ip)},
            "name": f"OpenWRT {self._ip}",
            "manufacturer": "OpenWRT",
            "model": "Router",
        }

