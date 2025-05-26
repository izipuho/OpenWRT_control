"""Select entities declaration."""

import logging

from homeassistant.components.select import SelectEntity
from homeassistant.const import EntityCategory
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .config_loader import load_config_types
from .const import CONFIG_TYPES_PATH, get_device_info
from .coordinator import OpenWRTDataCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Asyncronious entry setup."""
    devices = config_entry.data.get("devices", [])

    config_types_path = hass.config.path(CONFIG_TYPES_PATH)
    config_type_options = await hass.async_add_executor_job(
        load_config_types, config_types_path
    )
    name_to_key = {v["name"]: k for k, v in config_type_options.items()}
    key_to_name = {k: v["name"] for k, v in config_type_options.items()}

    entities = []
    for device in devices:
        ip = device["ip"]
        config_type = device["config_type"]

        coordinator = OpenWRTDataCoordinator(hass, ip, config_type)

        entities.extend(
            [
                OpenWRTSelect(
                    coordinator,
                    ip,
                    "Config Type",
                    static_value=config_type,
                    entity_icon="mdi:cog",
                    entity_category=EntityCategory.CONFIG,
                    name_to_key=name_to_key,
                    key_to_name=key_to_name,
                ),
            ]
        )

    async_add_entities(entities, update_before_add=True)


class OpenWRTSelect(CoordinatorEntity, SelectEntity):
    """Select entities declaration."""

    def __init__(
        self,
        coordinator,
        ip: str,
        name: str,
        *,
        static_value: str | None = None,
        entity_icon: str | None = None,
        entity_category: EntityCategory | None = None,
        name_to_key: dict[str, str],
        key_to_name: dict[str, str],
    ) -> None:
        """Initialize select entity."""
        super().__init__(coordinator)
        self._ip = ip
        self._name = name
        self._attr_name = f"{name} ({ip})"
        self._attr_unique_id = f"{ip}_{name.lower().replace(' ', '_')}"
        # self._key = key
        self._attr_icon = entity_icon
        self._attr_entity_category = entity_category
        self._current_key = static_value
        self._attr_has_entity_name = True
        self._name_to_key = name_to_key or {}
        self._key_to_name = key_to_name or {}
        self._attr_options = list(self._key_to_name.values())
        # self._attr_current_option = self._key_to_name(self._current_key)
        self._attr_device_info = get_device_info(ip)

    @property
    def current_option(self):
        return self._key_to_name.get(self._current_key)

    @property
    def should_poll(self):
        return False

    @property
    def available(self):
        return True


# async def async_select_option(self, selected_option: str):
#    """Asyncronious select option definition."""
#    # store the key based on user selection
#    selected_key = self._name_to_key.get(selected_option)
#    if selected_key:
#        _LOGGER.debug(
#            "Selected option for %s: %s (%s)",
#            self._ip,
#            selected_option,
#            selected_key,
#        )
#        self._current_key = selected_key
#        self.async_write_ha_state()
#    else:
#        _LOGGER.warning("Selected unknown option: %s", selected_option)
