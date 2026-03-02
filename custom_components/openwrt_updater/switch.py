"""OpenWRT switch entities."""

import logging

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.restore_state import RestoreEntity

from .helpers.const import get_device_info
from .helpers.helpers import load_device_option, save_device_option

_LOGGER = logging.getLogger(__name__)


class OpenWRTSwitch(SwitchEntity, RestoreEntity):
    """Represent an OpenWRT switch entity."""

    def __init__(
        self,
        entry: ConfigEntry,
        ip: str,
        name: str,
        key: str,
        default_state: bool = False,
        entity_category: EntityCategory = None,
    ) -> None:
        """Initialize the switch entity."""
        # helpers
        self._entry = entry
        self._key = key
        self._default_state = default_state
        place_name = entry.data["place_name"]

        # device properties
        self._ip = ip
        self._name = name
        self._attr_device_info = get_device_info(place_name, self._ip)

        # base entity properties
        self._attr_name = f"{self._name} ({self._ip})"
        self._attr_unique_id = f"{name.lower().replace(' ', '_')}_{self._ip}"
        self._attr_entity_category = entity_category

        # specific entity properties
        self._attr_is_on = load_device_option(
            self._entry,
            self._ip,
            self._key,
            self._default_state,
        )

        _LOGGER.debug("%r", self)

    async def async_added_to_hass(self):
        """Restore the saved value when the entity is added."""
        await super().async_added_to_hass()
        self._attr_is_on = load_device_option(
            self._entry,
            self._ip,
            self._key,
            self._default_state,
        )

    @property
    def is_on(self) -> bool:
        """Return whether the switch is on."""
        return self._attr_is_on

    async def async_turn_on(self, **kwargs):
        """Turn the switch on."""
        self._attr_is_on = True
        save_device_option(
            self.hass,
            self._entry,
            self._ip,
            self._key,
            self._attr_is_on,
        )
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs):
        """Turn the switch off."""
        self._attr_is_on = False
        save_device_option(
            self.hass,
            self._entry,
            self._ip,
            self._key,
            self._attr_is_on,
        )
        self.async_write_ha_state()

    def __repr__(self):
        """Return a debug string representation."""
        repr_str = f"\nName: {self.name}"
        repr_str += f"\n\tClass: {self.device_class}"
        repr_str += f"\n\tState: {self._attr_is_on}"
        repr_str += f"\n\tCat: {self.entity_category}"
        return repr_str


async def async_setup_entry(hass: HomeAssistant, config_entry, async_add_entities):
    """Set up switch entities for a config entry."""
    devices = list(config_entry.options.get("devices", {}).keys())

    entities = []
    for ip in devices:
        entities.extend(
            [
                OpenWRTSwitch(
                    entry=config_entry,
                    ip=ip,
                    name="Simple update",
                    key="simple_update",
                    default_state=True,
                    entity_category=EntityCategory.CONFIG,
                ),
                OpenWRTSwitch(
                    entry=config_entry,
                    ip=ip,
                    name="Force update",
                    key="force_update",
                    default_state=False,
                    entity_category=EntityCategory.CONFIG,
                ),
            ]
        )

    async_add_entities(entities, update_before_add=True)
