"""Initialize OpenWRT Updater integration."""

import logging
import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
import homeassistant.helpers.config_validation as cv

from .const import DOMAIN
from .coordinator import OpenWRTDataCoordinator

_LOGGER = logging.getLogger(__name__)

CONFIG_SCHEMA = vol.Schema(
        {
            vol.Optional(DOMAIN, default={}): vol.Schema(
                {
                    vol.Optional("master_node", default="zip@10.8.25.20"): cv.string,
                    vol.Optional("builder_location", default="/home/zip/OpenWrt-bulder/"): cv.string,
                    vol.Optional("ssh_key_path", default="/config/ssh_keys/id_ed25519"): cv.string,
                }
            )
        },
        extra=vol.ALLOW_EXTRA
)

PLATFORMS = [
    "binary_sensor",
    #"button",
    "select",
    "switch",
    "text",
    "update",
]


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Этот хук вызывается первым, при старте HA, для всех YAML-настроек."""
    # Берём из parsed configuration.yaml ваш раздел, или {} по умолчанию
    yaml_conf = config.get(DOMAIN, {})

    # Сохраняем YAML-параметры в hass.data[DOMAIN]
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN]["config"] = yaml_conf

    # Не создаём import-flow: просто читаем и храним — всё
    return True

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up config entry."""
    _LOGGER.debug(
        "Entry data init: %s\nEntry options init: %s", entry.data, entry.options
    )

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {}

    devices = entry.options.get("devices", [])

    # Initial refresh — must be awaited here before loading platforms
    for ip, device in devices.items():
        hass.data[DOMAIN][entry.entry_id][ip] = dict(device)
        coordinator = OpenWRTDataCoordinator(hass, ip)
        await coordinator.async_config_entry_first_refresh()
        hass.data[DOMAIN][entry.entry_id][ip].update(coordinator.data)
        _LOGGER.debug("Initial HAss data: %s", hass.data[DOMAIN][entry.entry_id][ip])

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Reload entry."""
    await async_setup_entry(hass, entry)
    await async_unload_entry(hass, entry)
    return True
