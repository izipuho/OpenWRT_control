"""Binary sensor declaration."""

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import get_device_info
from .coordinator import OpenWRTDataCoordinator


async def async_setup_entry(hass: HomeAssistant, config_entry, async_add_entities):
    """Asyncronious entry setup."""
    devices = config_entry.data.get("devices", [])

    entities = []
    for device in devices:
        ip = device["ip"]
        config_type = device["config_type"]

        coordinator = OpenWRTDataCoordinator(hass, ip, config_type)

        entities.extend(
            [
                OpenWRTBinarySensor(
                    coordinator,
                    ip,
                    "Status",
                    "status",
                    BinarySensorDeviceClass.CONNECTIVITY,
                    EntityCategory.DIAGNOSTIC,
                ),
            ]
        )

    async_add_entities(entities, update_before_add=True)


class OpenWRTBinarySensor(CoordinatorEntity, BinarySensorEntity):
    """OpenWRT binary sensors class."""

    def __init__(
        self,
        coordinator,
        ip: str,
        name: str,
        key: str,
        device_class: BinarySensorDeviceClass,
        entity_category: EntityCategory = None,
    ) -> None:
        """Initialize binary sensor class."""
        super().__init__(coordinator)
        self._ip = ip
        self._name = name
        self._key = key
        self._attr_name = f"{name} ({ip})"
        self._attr_unique_id = f"{ip}_{name.lower().replace(' ', '_')}"
        self._attr_device_class = device_class
        self._attr_entity_category = entity_category
        self._attr_device_info = get_device_info(ip)

    @property
    def is_on(self):
        """Return device status."""
        if self.coordinator.data is None:
            return False
        return self.coordinator.data.get(self._key) == "online"

    @property
    def available(self):
        """Return last successfull update."""
        return self.coordinator.last_update_success
