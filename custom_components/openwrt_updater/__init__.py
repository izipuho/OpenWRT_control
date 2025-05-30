"""Initialize OpenWRT Updater integration."""
##TODO prettify select (name instead code)
##TODO validate IP

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .coordinator import OpenWRTDataCoordinator

_LOGGER = logging.getLogger(__name__)

# PLATFORMS = ["binary_sensor", "select", "switch", "text", "update"]
PLATFORMS = ["binary_sensor", "text", "update"]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up config entry."""
    _LOGGER.debug("Entry data: %s", entry.data)

    coordinator = OpenWRTDataCoordinator(
        hass,
        entry,
        entry.data["devices"][0]["ip"],
        entry.data["devices"][0]["config_type"],
    )

    # Initial refresh — must be awaited here before loading platforms
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {"devices": entry.data.get("devices", [])}
    # hass.data[DOMAIN][entry.entry_id] = {"coodinator": coordinator}

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
