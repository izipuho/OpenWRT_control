"""OpenWRT binary sensor entities."""

import logging

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .helpers.const import DOMAIN, get_device_info

_LOGGER = logging.getLogger(__name__)


class OpenWRTBinarySensor(CoordinatorEntity, BinarySensorEntity):
    """Represent an OpenWRT binary sensor entity."""

    def __init__(
        self,
        coordinator,
        place_name: str,
        ip: str,
        name: str,
        key: str,
        device_class: BinarySensorDeviceClass = None,
        entity_category: EntityCategory = None,
    ) -> None:
        """Initialize the binary sensor entity."""
        super().__init__(coordinator)

        # device properties
        self._ip = ip
        self._name = name
        self._attr_device_info = get_device_info(place_name, ip)

        # base entity properties
        self._key = key
        self._attr_name = f"{name} ({ip})"
        self._attr_unique_id = f"{name.lower().replace(' ', '_')}_{ip}"
        self._attr_entity_category = entity_category

        # specific entity properties
        self._attr_device_class = device_class

        _LOGGER.debug("%r", self)

    @property
    def is_on(self) -> bool:
        """Return the current sensor state."""
        if self.coordinator.data is None:
            return False
        return self.coordinator.data.get(self._key)

    @property
    def available(self):
        """Return whether the latest coordinator update succeeded."""
        return self.coordinator.last_update_success

    def __repr__(self):
        """Return a debug string representation."""
        repr_str = f"\nName: {self.name}"
        repr_str += f"\n\tClass: {self.device_class}"
        repr_str += f"\n\tCat: {self.entity_category}"
        return repr_str


async def async_setup_entry(hass: HomeAssistant, config_entry, async_add_entities):
    """Set up binary sensor entities for a config entry."""
    place_name = config_entry.data["place_name"]
    devices = list(config_entry.options.get("devices", {}).keys())

    entities = []
    for ip in devices:
        coordinator = hass.data[DOMAIN][config_entry.entry_id][ip]["coordinator"]
        entities.extend(
            [
                OpenWRTBinarySensor(
                    coordinator,
                    place_name,
                    ip,
                    "Status",
                    "status",
                    device_class=BinarySensorDeviceClass.CONNECTIVITY,
                    entity_category=EntityCategory.DIAGNOSTIC,
                ),
                OpenWRTBinarySensor(
                    coordinator,
                    place_name,
                    ip,
                    "Firmware downloaded",
                    "firmware_downloaded",
                    device_class=BinarySensorDeviceClass.OCCUPANCY,
                    entity_category=EntityCategory.DIAGNOSTIC,
                ),
                OpenWRTBinarySensor(
                    coordinator,
                    place_name,
                    ip,
                    "Has ASU client",
                    "has_asu_client",
                    device_class=BinarySensorDeviceClass.OCCUPANCY,
                    entity_category=EntityCategory.DIAGNOSTIC,
                ),
            ]
        )

    async_add_entities(entities, update_before_add=True)
