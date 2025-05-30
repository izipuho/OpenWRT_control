"""Select entities declaration."""
# TODO persist state
# TODO prettify select (name instead code)

import logging

from homeassistant.components.select import SelectEntity
from homeassistant.const import EntityCategory
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .config_loader import load_config_types
from .const import CONFIG_TYPES_PATH, get_device_info
from .coordinator import OpenWRTDataCoordinator

_LOGGER = logging.getLogger(__name__)


class OpenWRTSelect(CoordinatorEntity, SelectEntity):
    """Select entities declaration."""

    def __init__(
        self,
        coordinator: OpenWRTDataCoordinator,
        entry,
        device,
        ip: str,
        name: str,
        *,
        current_value: str | None = None,
        entity_icon: str | None = None,
        entity_category: EntityCategory | None = None,
        config_type_options: list[str],
    ) -> None:
        """Initialize select entity."""
        super().__init__(coordinator)
        self.coordinator = coordinator
        # device properties
        self._ip = ip
        self._name = name
        self._attr_device_info = get_device_info(ip)
        self.entry = entry
        self.device = device

        # base entry properties
        self._attr_name = f"{name} ({ip})"
        self._attr_unique_id = f"{name.lower().replace(' ', '_')}_{ip}"
        self._attr_icon = entity_icon
        self._attr_entity_category = entity_category

        # specific entry properties
        self._current_value = current_value
        ##self._attr_has_entity_name = True
        self._attr_options = sorted(config_type_options.keys())

        # dunno
        self._attr_available = True
        self._attr_should_poll = False

        # helpers
        self._config_type_options = config_type_options

        _LOGGER.debug(repr(self))

    @property
    def current_option(self):
        """Return current option."""
        data = self.coordinator.data or {}
        return data.get(self._ip, {}).get("config_type", self._current_value)

    async def async_select_option(self, option: str) -> None:
        """Select option."""
        self._attr_current_option = option

        # update in memory coordinator
        if self._ip in self.coordinator.data:
            self.coordinator.data[self._ip]["config_type"] = option
        else:
            self.coordinator.data[self._ip] = {"config_type": option}

        # update config entry
        entry = self.coordinator.config_entry
        devices = entry.options.get("devices", [])
        for device in devices:
            if device["ip"] == self._ip:
                device["config_type"] = option
                break

        self.hass.config_entries.async_update_entry(entry, options={"devices": devices})

        self.async_write_ha_state()

    def __repr__(self):
        """Repesent the object."""
        repr_str = f"\nName: {self.name}"
        repr_str += f"\n\tClass: {self.device_class}"
        repr_str += f"\n\tValue: {self._current_value}"
        repr_str += f"\n\tCat: {self.entity_category}"
        return repr_str


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Asyncronious entry setup."""
    devices = config_entry.data.get("devices", [])

    config_types_path = hass.config.path(CONFIG_TYPES_PATH)
    config_type_options = await hass.async_add_executor_job(
        load_config_types, config_types_path
    )

    entities = []
    for device in devices:
        ip = device["ip"]
        config_type = device["config_type"]

        coordinator = OpenWRTDataCoordinator(hass, config_entry, ip, config_type)

        entities.extend(
            [
                OpenWRTSelect(
                    coordinator,
                    config_entry,
                    device,
                    ip,
                    "Config Type",
                    current_value=config_type,
                    entity_icon="mdi:cog",
                    entity_category=EntityCategory.CONFIG,
                    config_type_options=config_type_options,
                ),
            ]
        )

    async_add_entities(entities, update_before_add=True)
