"""Simple update declaration."""

import logging

from homeassistant.components.switch import SwitchEntity
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import get_device_info
from .coordinator import OpenWRTDataCoordinator

_LOGGER = logging.getLogger(__name__)


class OpenWRTSwitch(CoordinatorEntity, SwitchEntity):
    """OpenWRT simple update class."""

    def __init__(
        self,
        coordinator: OpenWRTDataCoordinator,
        ip: str,
        name: str,
        key: str,
        state: bool,
        entity_category: EntityCategory = None,
    ) -> None:
        """Initialize simple update class."""
        # helpers
        self.entry = coordinator.config_entry
        self.devices = self.entry.data.get("devices", [])
        device = next((d for d in self.devices if d.get("ip") == ip), {})
        self._key = key

        super().__init__(coordinator)
        # device properties
        self._ip = ip
        self._name = name
        self._attr_device_info = get_device_info(ip)

        # base entity properties
        self._attr_name = f"{name} ({ip})"
        self._attr_unique_id = f"{name.lower().replace(' ', '_')}_{ip}"
        self._attr_entity_category = entity_category

        # specific entity properties
        self._attr_is_on = device.get("simple_update", state)

        _LOGGER.debug(repr(self))

    async def async_turn_on(self, **kwargs):
        """Turn on."""
        self._attr_is_on = True
        self.async_write_ha_state()
        await self._persist_state(self._attr_is_on)

    async def async_turn_off(self, **kwargs):
        """Turn off."""
        self._attr_is_on = False
        self.async_write_ha_state()
        await self._persist_state(self._attr_is_on)

    async def _persist_state(self, value: bool):
        # Persist the state in config entry options
        updated_device = []

        for d in self.devices:
            if d.get("ip") == self._ip:
                d[self._key] = value
            updated_device.append(d)

        self.hass.config_entries.async_update_entry(
            self.entry, options={"devices": updated_device}
        )

    def __repr__(self):
        """Repesent the object."""
        repr_str = f"\nName: {self.name}"
        repr_str += f"\n\tClass: {self.device_class}"
        repr_str += f"\n\tState: {self._attr_is_on}"
        repr_str += f"\n\tCat: {self.entity_category}"
        return repr_str


async def async_setup_entry(hass: HomeAssistant, config_entry, async_add_entities):
    """Asyncronious entry setup."""
    devices = config_entry.data.get("devices", [])
    coordinator = OpenWRTDataCoordinator(hass, config_entry)

    entities = []
    for device in devices:
        ip = device["ip"]
        state = device["is_simple"]

        entities.extend(
            [
                OpenWRTSwitch(
                    coordinator,
                    ip,
                    "Simple update",
                    "simple_update",
                    state,
                    EntityCategory.CONFIG,
                ),
                OpenWRTSwitch(
                    coordinator,
                    ip,
                    "Force update",
                    "force_update",
                    state,
                    EntityCategory.CONFIG,
                ),
            ]
        )

    async_add_entities(entities, update_before_add=True)
