"""Select entities declaration."""
# TODO prettify select (name instead code)

import logging

from homeassistant.components.select import SelectEntity
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONFIG_TYPES_PATH, get_device_info
from .coordinator import OpenWRTDataCoordinator
from .helpers import load_config_types, load_device_option, save_device_option

_LOGGER = logging.getLogger(__name__)


class OpenWRTSelect(CoordinatorEntity, SelectEntity):
    """Select entities declaration."""

    def __init__(
        self,
        coordinator: OpenWRTDataCoordinator,
        ip: str,
        name: str,
        key: str,
        *,
        current_value: str | None = None,
        entity_icon: str | None = None,
        entity_category: EntityCategory | None = None,
        config_types: list[str],
    ) -> None:
        """Initialize select entity."""
        super().__init__(coordinator)
        # helpers
        self._config_types = config_types
        self._key = key

        # device properties
        self._ip = ip
        self._name = name
        self._attr_device_info = get_device_info(self._ip)

        # base entry properties
        self._attr_name = f"{name} ({self._ip})"
        self._attr_unique_id = f"{name.lower().replace(' ', '_')}_{self._ip}"
        self._attr_icon = entity_icon
        self._attr_entity_category = entity_category

        # specific entry properties
        self._current_value = current_value
        # self._attr_current_option = load_device_option(
        #    self.coordinator.config_entry, self._ip, self._key, current_value
        # )
        self._attr_options = sorted(config_types.keys())
        self._attr_available = True
        self._attr_should_poll = False

        _LOGGER.debug(repr(self))

    @property
    def current_option(self):
        """Return current option."""
        return load_device_option(
            self.coordinator.config_entry, self._ip, self._key, self._current_value
        )

    async def async_select_option(self, option: str) -> None:
        """Select option."""
        self._attr_current_option = option
        self._current_value = option
        _LOGGER.debug("Select option: %s", option)
        save_device_option(
            self.hass,
            self.coordinator.config_entry,
            self._ip,
            self._key,
            option,
        )
        self.async_write_ha_state()

    def __repr__(self):
        """Repesent the object."""
        repr_str = f"\nName: {self.name}"
        repr_str += f"\n\tClass: {self.device_class}"
        repr_str += f"\n\tValue: {self._current_value}"
        repr_str += f"\n\tCat: {self.entity_category}"
        return repr_str


async def async_setup_entry(hass: HomeAssistant, config_entry, async_add_entities):
    """Asyncronious entry setup."""
    devices = config_entry.options.get("devices", {})

    config_types_path = hass.config.path(CONFIG_TYPES_PATH)
    config_types = await hass.async_add_executor_job(
        load_config_types, config_types_path
    )

    entities = []
    for ip, device in devices.items():
        config_type = device["config_type"]
        coordinator = OpenWRTDataCoordinator(hass, ip)

        entities.extend(
            [
                OpenWRTSelect(
                    coordinator,
                    ip,
                    "Config Type",
                    "config_type",
                    current_value=config_type,
                    entity_icon="mdi:cog",
                    entity_category=EntityCategory.CONFIG,
                    config_types=config_types,
                ),
            ]
        )

    async_add_entities(entities, update_before_add=True)
