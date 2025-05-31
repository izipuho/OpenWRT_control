"""Simple update declaration."""
##TODO persist state

from homeassistant.components.switch import SwitchEntity
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import get_device_info
from .coordinator import OpenWRTDataCoordinator
import logging

_LOGGER = logging.getLogger(__name__)


class OpenWRTSimpleUpdate(CoordinatorEntity, SwitchEntity):
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
        entry = coordinator.config_entry
        devices = entry.options.get("devices", [])
        device = next((d for d in devices if d.get("ip") == ip), {})
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
        self._attr_is_on = device.get("is_simple", state)

        _LOGGER.warning(repr(self))

    def turn_on(self, **kwargs):
        """Turn on handler."""
        self._attr_is_on = True
        self.async_write_ha_state()

    def turn_off(self, **kwargs):
        """Turn off handler."""
        self._attr_is_on = False
        self.async_write_ha_state()

    async def async_turn_on(self, **kwargs):
        """Turn on."""
        self.turn_on()

    async def async_turn_off(self, **kwargs):
        """Turn off."""
        self.turn_off()

    async def _set_simple_update(self, value: bool):
        self._attr_is_on = value
        self.async_write_ha_state()

        # Persist the state in config entry options
        entry = self.coordinator.config_entry
        devices = entry.options.get("devices", [])
        new_devices = []

        for d in devices:
            if d.get("ip") == self._ip:
                d["is_simple"] = value
            new_devices.append(d)

        self.hass.config_entries.async_update_entry(
            entry, options={"devices": new_devices}
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
                OpenWRTSimpleUpdate(
                    coordinator,
                    ip,
                    "Simple update",
                    "is_simple",
                    state,
                    EntityCategory.CONFIG,
                ),
            ]
        )

    async_add_entities(entities, update_before_add=True)
