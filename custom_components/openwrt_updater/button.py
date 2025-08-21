"""Simple update declaration."""

import logging

from homeassistant.components.button import ButtonEntity
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, get_device_info

_LOGGER = logging.getLogger(__name__)


class OpenWRTButton(CoordinatorEntity, ButtonEntity):
    """OpenWRT simple update class."""

    def __init__(
        self,
        coordinator,
        config_entry,
        device: dict,
        name: str,
        key: str,
        entity_category: EntityCategory,
    ) -> None:
        """Initialize simple update class."""
        super().__init__(coordinator)

        # helpers
        self._device = device
        self._key = key

        # device properties
        self._ip = self._device["ip"]
        self._name = name
        self._attr_device_info = get_device_info(device["place_name"], self._ip)
        self._config_entry = config_entry

        # base entity properties
        self._attr_name = f"{name} ({self._ip})"
        self._attr_unique_id = f"{name.lower().replace(' ', '_')}_{self._ip}"
        self._attr_entity_category = entity_category

        # specific entity properties

        _LOGGER.debug(repr(self))

    async def async_press(self) -> None:
        """Handle button press."""
        #   await self.coordinator.async_config_entry_first_refresh()
        #   _LOGGER.warning(
        #       "DEBUG coordinator data for %s: %s",
        #       self._ip,
        #       self.coordinator.data,
        #   )
        #   _LOGGER.warning(
        #       "DEBUG entry options for %s: %s",
        #       self._ip,
        #       self.coordinator.config_entry.options.get("devices", {}).get(self._ip, {}),
        #   )
        #   _LOGGER.warning(
        #       "DEBUG HAss data for %s: %s",
        #       self._ip,
        #       self.hass.data[DOMAIN][self.coordinator.config_entry.entry_id][self._ip],
        #   )
        #   _LOGGER.warning(
        #       "DEBUG HAss config: %s",
        #       self.hass.data[DOMAIN]["config"],
        #   )
        _LOGGER.error("All domain data: %s", self.hass.data[DOMAIN])
        _LOGGER.warning(
            "Entry data: %s | options: %s",
            self._config_entry.data,
            self._config_entry.options,
        )

    def __repr__(self):
        """Repesent the object."""
        repr_str = f"\nName: {self.name}"
        repr_str += f"\n\tCat: {self.entity_category}"
        return repr_str


async def async_setup_entry(hass: HomeAssistant, config_entry, async_add_entities):
    """Asyncronious entry setup."""
    place = config_entry.data
    devices = config_entry.options.get("devices", {})

    entities = []
    for ip, device in devices.items():
        coordinator = hass.data[DOMAIN][config_entry.entry_id][ip]["coordinator"]
        device["place_name"] = place["place_name"]
        entities.extend(
            [
                OpenWRTButton(
                    coordinator=coordinator,
                    config_entry=config_entry,
                    device=device,
                    name="Debug",
                    key="debug",
                    entity_category=EntityCategory.DIAGNOSTIC,
                ),
            ]
        )

    async_add_entities(entities, update_before_add=True)
