"""OpenWRT button entities."""

import logging

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .coordinators.device import OpenWRTDeviceCoordinator
from .helpers.const import DOMAIN, get_device_info, get_place_device_info
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
            await apply_wifi_policy(
                self.coordinator, resolve_wifi_policy(self.hass, self._config_entry, self._ip), True)

        elif self._key == "reboot":
            _key_path = self.hass.data[DOMAIN]["config"]["ssh_key_path"]
            async with OpenWRTSSH(self._ip, _key_path) as client:
                result = await client.exec_command("reboot", timeout=1800)
                _LOGGER.warning("Reboot command ended with %s", result)
            await self.coordinator.async_wait_for_alive()
        elif self._key == "apply_wifi_policy":
            applied = await apply_wifi_policy(
                self.coordinator,
                resolve_wifi_policy(self.hass, self._config_entry, self._ip),
                False,
            )
            if not applied:
                _LOGGER.warning("Wi-Fi policy apply failed for %s", self._ip)
            await self.coordinator.async_request_refresh()

    def __repr__(self):
        """Return a debug string representation."""
        repr_str = f"\nName: {self.name}"
        repr_str += f"\n\tCat: {self.entity_category}"
        return repr_str


class OpenWRTPlaceButton(ButtonEntity):
    """Represent a place-level OpenWRT action button."""

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: ConfigEntry,
        name: str,
        key: str,
        entity_category: EntityCategory,
        entity_icon: str | None = None,
    ) -> None:
        """Initialize the place button entity."""
        self.hass = hass
        self._config_entry = config_entry
        self._key = key
        self._place_name = str(config_entry.data.get("place_name", ""))

        self._attr_device_info = get_place_device_info(self._place_name)
        self._attr_name = f"{name} ({self._place_name})"
        self._attr_unique_id = (
            f"{key}_{self._place_name.lower().replace(' ', '_')}"
        )
        self._attr_entity_category = entity_category
        self._attr_icon = entity_icon

    async def async_press(self) -> None:
        """Handle place button press."""
        if self._key == "apply_wifi_policy_all":
            entry_data = self.hass.data[DOMAIN].get(self._config_entry.entry_id, {})
            devices = self._config_entry.options.get("devices", {})
            ok_count = 0
            fail_count = 0

            for ip in devices:
                coordinator = entry_data.get(ip, {}).get("coordinator")
                if coordinator is None:
                    fail_count += 1
                    continue

                applied = await apply_wifi_policy(
                    coordinator,
                    resolve_wifi_policy(self.hass, self._config_entry, ip),
                    False,
                )
                if applied:
                    ok_count += 1
                else:
                    fail_count += 1

                await coordinator.async_request_refresh()

            _LOGGER.warning(
                "Place Wi-Fi policy apply (%s): success=%s failed=%s",
                self._place_name,
                ok_count,
                fail_count,
            )


async def async_setup_entry(hass: HomeAssistant, config_entry, async_add_entities):
    """Set up button entities for a config entry."""
    devices = config_entry.options.get("devices", {})

    entities = []
    if devices:
        entities.append(
            OpenWRTPlaceButton(
                hass=hass,
                config_entry=config_entry,
                name="Apply Wi-Fi Policy (All)",
                key="apply_wifi_policy_all",
                entity_category=EntityCategory.CONFIG,
                entity_icon="mdi:wifi-cog",
            )
        )

    for ip in devices:
        coordinator = hass.data[DOMAIN][config_entry.entry_id][ip]["coordinator"]
        entities.extend(
            [
                OpenWRTButton(
                    coordinator=coordinator,
                    config_entry=config_entry,
                    ip=ip,
                    name="Apply Wi-Fi Policy",
                    key="apply_wifi_policy",
                    entity_category=EntityCategory.CONFIG,
                    entity_icon="mdi:wifi-cog",
                ),
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
