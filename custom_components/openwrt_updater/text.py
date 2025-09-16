"""Text entities declaration."""

import logging

from homeassistant.components.text import TextEntity
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .coordinators.device import OpenWRTDeviceCoordinator
from .helpers.const import DOMAIN, get_device_info

_LOGGER = logging.getLogger(__name__)


class OpenWRTText(CoordinatorEntity, TextEntity):
    """Text entities declaration."""

    def __init__(
        self,
        coordinator: OpenWRTDeviceCoordinator,
        place_name: str,
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
        self._attr_device_info = get_device_info(place_name, self._ip)

        # base entity properties
        self._key = key
        self._static_value = static_value
        self._attr_name = f"{name} ({self._ip})"
        self._attr_unique_id = f"{name.lower().replace(' ', '_')}_{self._ip}"
        self._attr_icon = entity_icon
        self._attr_entity_category = entity_category
        _LOGGER.debug("%r", self)

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
        repr_str += f"\n\tValue: {self.value}"
        return repr_str


async def async_setup_entry(hass: HomeAssistant, config_entry, async_add_entities):
    """Asyncronious entry setup."""
    place_name = config_entry.data["place_name"]
    devices = list(config_entry.options.get("devices", {}).keys())

    entities = []
    for ip in devices:
        coordinator = hass.data[DOMAIN][config_entry.entry_id][ip]["coordinator"]
        entities.extend(
            [
                OpenWRTText(
                    coordinator,
                    place_name,
                    ip,
                    "IP Address",
                    static_value=ip,
                    entity_icon="mdi:ip-network",
                ),
                OpenWRTText(
                    coordinator,
                    place_name,
                    ip,
                    "Device Name",
                    key="hostname",
                    entity_icon="mdi:router-network",
                ),
            ]
        )

    async_add_entities(entities, update_before_add=True)
