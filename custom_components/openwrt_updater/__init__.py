"""Initialize OpenWRT Updater integration."""

import logging
from pathlib import Path

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .coordinator import OpenWRTDataCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [
    "binary_sensor",
    # "button",
    "select",
    "switch",
    "text",
    "update",
]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up config entry."""
    _LOGGER.warning(
        "OpenWRT Control: setup_entry id=%s source=%s title=%s",
        entry.entry_id,
        entry.source,
        entry.title,
    )
    # Create empty config-entry dict
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {}

    if entry.unique_id == "__global__":
        component_config = dict(entry.options)

        ssh_key_path = hass.config.path(component_config.get("ssh_key_path"))
        config_types_path = str(
            Path(__file__).parent / component_config.get("config_types_file")
        )

        # Save it to hass.data[DOMAIN]
        hass.data.setdefault(DOMAIN, {})
        hass.data[DOMAIN]["config"] = component_config
        hass.data[DOMAIN]["config"]["ssh_key_path"] = ssh_key_path
        hass.data[DOMAIN]["config"]["config_types_path"] = config_types_path
    else:
        # Get devices info from config_entry
        devices = entry.options.get("devices", [])

        # Save config-entry and coordinator data to hass.data for each device
        for ip, device in devices.items():
            # Config-entry data
            hass.data[DOMAIN][entry.entry_id][ip] = dict(device)
            # Coordinator data
            coordinator = OpenWRTDataCoordinator(hass, ip)
            await coordinator.async_config_entry_first_refresh()
            hass.data[DOMAIN][entry.entry_id][ip].update(coordinator.data)

            _LOGGER.debug(
                "Initial HAss data: %s", hass.data[DOMAIN][entry.entry_id][ip]
            )

        # Initialize all platforms
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
