"""Binary sensor declaration."""

import logging

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import get_device_info
from .coordinator import OpenWRTDataCoordinator

_LOGGER = logging.getLogger(__name__)


class OpenWRTBinarySensor(CoordinatorEntity, BinarySensorEntity):
    """OpenWRT binary sensors class."""

    def __init__(
        self,
        coordinator: OpenWRTDataCoordinator,
        ip: str,
        name: str,
        key: str,
        device_class: BinarySensorDeviceClass = None,
        entity_category: EntityCategory = None,
    ) -> None:
        """Initialize binary sensor class."""
        super().__init__(coordinator)

        # device properties
        self._ip = ip
        self._name = name
        self._attr_device_info = get_device_info(ip)

        # base entity properties
        self._key = key
        self._attr_name = f"{name} ({ip})"
        self._attr_unique_id = f"{name.lower().replace(' ', '_')}_{ip}"
        self._attr_entity_category = entity_category

        # specific entity properties
        self._attr_device_class = device_class

        _LOGGER.debug(repr(self))

    @property
    def is_on(self) -> bool:
        """Return device status."""
        if self.coordinator.data is None:
            return False
        # return self.coordinator.data.get(self._ip).get(self._key) == "on"
        return self.coordinator.data.get(self._ip).get(self._key)

    @property
    def available(self):
        """Return last successfull update."""
        return self.coordinator.last_update_success

    def __repr__(self):
        """Repesent the object."""
        repr_str = f"\nName: {self.name}"
        repr_str += f"\n\tClass: {self.device_class}"
        repr_str += f"\n\tCat: {self.entity_category}"
        return repr_str


async def async_setup_entry(hass: HomeAssistant, config_entry, async_add_entities):
    """Asyncronious entry setup."""
    devices = config_entry.data.get("devices", [])
    coordinator = OpenWRTDataCoordinator(hass, config_entry)

    entities = []
    for device in devices:
        ip = device["ip"]

        entities.extend(
            [
                OpenWRTBinarySensor(
                    coordinator,
                    ip,
                    "Status",
                    "status",
                    device_class=BinarySensorDeviceClass.CONNECTIVITY,
                    entity_category=EntityCategory.DIAGNOSTIC,
                ),
                OpenWRTBinarySensor(
                    coordinator,
                    ip,
                    "Firmware downloaded",
                    "firmware_downloaded",
                    device_class=BinarySensorDeviceClass.OCCUPANCY,
                    entity_category=EntityCategory.DIAGNOSTIC,
                ),
            ]
        )

    async_add_entities(entities, update_before_add=True)
