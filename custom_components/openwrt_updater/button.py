"""Simple update declaration."""

import logging

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .coordinators.device import OpenWRTDeviceCoordinator
from .helpers.asu_client import ASUClient
from .helpers.const import DOMAIN, get_device_info
from .helpers.ssh_client import OpenWRTSSH
from .helpers.updater import OpenWRTUpdater
from .helpers.toh_builder import LocalTOH

_LOGGER = logging.getLogger(__name__)


class OpenWRTButton(CoordinatorEntity, ButtonEntity):
    """OpenWRT simple update class."""

    def __init__(
        self,
        coordinator: OpenWRTDeviceCoordinator,
        config_entry: ConfigEntry,
        ip: str,
        name: str,
        key: str,
        entity_category: EntityCategory,
    ) -> None:
        """Initialize simple update class."""
        super().__init__(coordinator)

        # helpers
        self._key = key
        place_name = config_entry.data["place_name"]

        # device properties
        self._ip = ip
        self._name = name
        self._attr_device_info = get_device_info(place_name, self._ip)
        self._config_entry = config_entry

        # base entity properties
        self._attr_name = f"{name} ({self._ip})"
        self._attr_unique_id = f"{name.lower().replace(' ', '_')}_{self._ip}"
        self._attr_entity_category = entity_category

        # specific entity properties

        _LOGGER.debug("%r", self)

    async def async_press(self) -> None:
        """Handle button press."""
        await self.coordinator.async_request_refresh()
        await self.hass.data[DOMAIN]["toh_index"].async_request_refresh()
        entry_data = self.hass.data[DOMAIN][self._config_entry.entry_id]
        dev = entry_data[self._ip]
        _LOGGER.error("Config: %s", self.hass.data[DOMAIN]["config"])
        _LOGGER.warning("Device data: %s", dev)
        _LOGGER.error("Coordinator data: %s", dev["coordinator"].data)

    def __repr__(self):
        """Repesent the object."""
        repr_str = f"\nName: {self.name}"
        repr_str += f"\n\tCat: {self.entity_category}"
        return repr_str


async def async_setup_entry(hass: HomeAssistant, config_entry, async_add_entities):
    """Asyncronious entry setup."""
    devices = config_entry.options.get("devices", {})

    entities = []
    for ip in devices:
        coordinator = hass.data[DOMAIN][config_entry.entry_id][ip]["coordinator"]
        entities.extend(
            [
                OpenWRTButton(
                    coordinator=coordinator,
                    config_entry=config_entry,
                    ip=ip,
                    name="Debug",
                    key="debug",
                    entity_category=EntityCategory.DIAGNOSTIC,
                ),
            ]
        )

    async_add_entities(entities, update_before_add=True)
