"""Updater entity declaration."""

import logging

from homeassistant.components.update import (
    UpdateDeviceClass,
    UpdateEntity,
    UpdateEntityFeature,
)
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .helpers.const import DOMAIN, get_device_info
from .helpers.updater import OpenWRTUpdater

_LOGGER = logging.getLogger(__name__)


class OpenWRTUpdateEntity(CoordinatorEntity, UpdateEntity):
    """Updater entity declaration."""

    def __init__(
        self,
        config_entry,
        coordinator,
        ip,  # ,
        # update_callback
    ) -> None:
        """Initialize updater entity."""
        super().__init__(coordinator)
        # helpers
        place_name = config_entry.data["place_name"]
        self.config_entry = config_entry

        # device properties
        self._ip = ip
        self._attr_device_info = get_device_info(place_name, self._ip)

        # base entity properties
        self._attr_name = f"Firmware ({self._ip})"
        self._attr_unique_id = f"firmware_{self._ip}"

        # specific entity properties
        self._attr_supported_features = UpdateEntityFeature.INSTALL
        self._attr_device_class = UpdateDeviceClass.FIRMWARE
        self._attr_extra_state_attributes = {"force": False}

        _LOGGER.debug("%r", self)

    @property
    def installed_version(self):
        """Return installed version."""
        if self.coordinator.data is None:
            return "unavailable"
        return self.coordinator.data.get("current_os_version")

    @property
    def latest_version(self):
        """Return available version."""
        if self.coordinator.data is None:
            return "unavailable"
        return self.coordinator.data.get("available_os_version")

    @property
    def available(self):
        """Return availability."""
        return self.coordinator.last_update_success

    @property
    def entity_picture(self):
        """Do not try to override picture."""
        return None

    def _can_install(self) -> bool:
        """Check intall possibility."""
        installed = self.installed_version
        latest = self.latest_version
        if not installed or not latest:
            return False
        return self.version_is_newer(latest, installed)

    @property
    def supported_features(self) -> UpdateEntityFeature:
        """Calc supported features."""
        features = UpdateEntityFeature(0)
        if self._can_install():
            features |= UpdateEntityFeature.INSTALL
        return features

    async def async_install(self, version: str | None, backup: bool, **kwargs):
        """Call update function."""
        # await self._update_callback(self.config_entry.entry_id, self._ip)
        updater = OpenWRTUpdater(self.hass, self.config_entry.entry_id, self._ip)
        result = await updater.trigger_upgrade()
        if not result.get("success", False):
            _LOGGER.error("Update failed for %s: %s", self._ip, result)
            raise HomeAssistantError(str(result.get("message", "")))
        await self.coordinator.async_request_refresh()
        await self.coordinator.async_wait_for_alive()

    def __repr__(self):
        """Represent the object."""
        repr_str = f"\nName: {self.name}"
        repr_str += f"\n\tValue: {self.latest_version}"
        return repr_str


async def async_setup_entry(hass: HomeAssistant, config_entry, async_add_entities):
    """Asyncronious entry setup."""
    devices = config_entry.options.get("devices", {})
    entities = []

    for ip in devices:
        coordinator = hass.data[DOMAIN][config_entry.entry_id][ip]["coordinator"]
        entities.extend(
            [
                OpenWRTUpdateEntity(
                    config_entry,
                    coordinator,
                    ip,
                ),
            ]
        )

    async_add_entities(entities, update_before_add=True)
