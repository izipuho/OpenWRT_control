"""OpenWRT button entities."""

import logging

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .coordinators.device import OpenWRTDeviceCoordinator
from .helpers.const import DOMAIN, get_device_info
from .helpers.ssh_client import OpenWRTSSH
from .helpers.wifi import apply_wifi_policy, resolve_wifi_policy

_LOGGER = logging.getLogger(__name__)


class OpenWRTButton(CoordinatorEntity, ButtonEntity):
    """Represent an OpenWRT button entity."""

    def __init__(
        self,
        coordinator: OpenWRTDeviceCoordinator,
        config_entry: ConfigEntry,
        ip: str,
        name: str,
        key: str,
        entity_category: EntityCategory,
        entity_icon: str | None = None,
    ) -> None:
        """Initialize the button entity."""
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
        self._attr_icon = entity_icon

        # specific entity properties

        _LOGGER.debug("%r", self)

    async def async_press(self) -> None:
        """Handle button press."""
        if self._key == "debug":
            await self.coordinator.async_request_refresh()
            await self.hass.data[DOMAIN]["toh_index"].async_request_refresh()

            entry_data = self.hass.data[DOMAIN][self._config_entry.entry_id]
            dev = entry_data[self._ip]

            _LOGGER.error("Place wifi data (%s): %s",
                          entry_data["data"]["place_name"], self._config_entry.options)

            _LOGGER.warning(
                "Device wifi roaming (%s): %s",
                self._ip,
                dev["coordinator"].data["wifi_roaming_enabled"],
            )
            _LOGGER.warning(
                "Device wifi ifaces (%s): %s",
                self._ip,
                dev["coordinator"].data["wifi_ifaces"],
            )
            _LOGGER.warning(
                "Device wifi radios (%s): %s",
                self._ip,
                dev["coordinator"].data["wifi_radios"],
            )
            _LOGGER.warning("WiFi policy to apply: %s", apply_wifi_policy(
                self.coordinator, resolve_wifi_policy(self.hass, self._config_entry, self._ip), True))

        elif self._key == "reboot":
            _key_path = self.hass.data[DOMAIN]["config"]["ssh_key_path"]
            async with OpenWRTSSH(self._ip, _key_path) as client:
                result = await client.exec_command("reboot", timeout=1800)
                _LOGGER.warning("Reboot command ended with %s", result)
            await self.coordinator.async_wait_for_alive()

    def __repr__(self):
        """Return a debug string representation."""
        repr_str = f"\nName: {self.name}"
        repr_str += f"\n\tCat: {self.entity_category}"
        return repr_str


async def async_setup_entry(hass: HomeAssistant, config_entry, async_add_entities):
    """Set up button entities for a config entry."""
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
                    entity_icon="mdi:bug-play",
                ),
                OpenWRTButton(
                    coordinator=coordinator,
                    config_entry=config_entry,
                    ip=ip,
                    name="Reboot",
                    key="reboot",
                    entity_category=EntityCategory.DIAGNOSTIC,
                    entity_icon="mdi:reload",
                ),
            ]
        )

    async_add_entities(entities, update_before_add=True)
