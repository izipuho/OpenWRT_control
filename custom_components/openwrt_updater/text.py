"""Text entities declaration."""
##TODO move config type back to select

import logging

from homeassistant.components.text import TextEntity
from homeassistant.const import EntityCategory
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import get_device_info
from .coordinator import OpenWRTDataCoordinator

_LOGGER = logging.getLogger(__name__)


class OpenWRTText(CoordinatorEntity, TextEntity):
    """Text entities declaration."""

    def __init__(
        self,
        coordinator: OpenWRTDataCoordinator,
        ip: str,
        name: str,
        *,
        key: str | None = None,
        static_value: str | None = None,
        entity_category: EntityCategory | None = None,
        entity_icon: str | None = None,
    ) -> None:
        """Initialize text entity."""
        super().__init__(coordinator)
        # helpers
        self.value = ""

        # device properties
        self._ip = ip
        self._name = name
        self._attr_device_info = get_device_info(ip)

        # base entity properties
        self._key = key
        self._static_value = static_value
        self._attr_name = f"{name} ({ip})"
        self._attr_unique_id = f"{name.lower().replace(' ', '_')}_{ip}"
        self._attr_icon = entity_icon
        self._attr_entity_category = entity_category
        _LOGGER.debug(repr(self))

    @property
    def native_value(self):
        """Return entity native value."""
        if self._key:
            self.value = (
                self.coordinator.data.get(self._key) if self.coordinator.data else None
            )
        else:
            self.value = self._static_value
        return self.value

    @property
    def available(self):
        """Return availability status."""
        return self.coordinator.last_update_success if self._key else True

    def __repr__(self):
        """Represent the object."""
        repr_str = f"\nName: {self.name}"
        repr_str += f"\n\tValue: {self.native_value}"
        return repr_str


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Asyncronious entry setup."""
    devices = config_entry.data.get("devices", [])

    entities = []
    for device in devices:
        ip = device["ip"]
        config_type = device["config_type"]

        coordinator = OpenWRTDataCoordinator(hass, config_entry, ip, config_type)

        entities.extend(
            [
                OpenWRTText(
                    coordinator,
                    ip,
                    "IP Address",
                    static_value=ip,
                    entity_icon="mdi:ip-network",
                ),
                OpenWRTText(
                    coordinator,
                    ip,
                    "Device Name",
                    key="hostname",
                    entity_icon="mdi:router-network",
                ),
                OpenWRTText(
                    coordinator,
                    ip,
                    "Snapshot URL",
                    key="snapshot_url",
                    entity_icon="mdi:link",
                    entity_category=EntityCategory.DIAGNOSTIC,
                ),
                OpenWRTText(
                    coordinator,
                    ip,
                    "Config type",
                    entity_icon="mdi:cog",
                    entity_category=EntityCategory.DIAGNOSTIC,
                    static_value=config_type,
                ),
            ]
        )

    async_add_entities(entities, update_before_add=True)
