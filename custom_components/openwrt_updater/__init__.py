"""Initialize OpenWRT Updater integration."""

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .coordinator import OpenWRTDataCoordinator  # Your coordinator class
from .options_flow import OpenWRTOptionsFlowHandler

_LOGGER = logging.getLogger(__name__)

PLATFORMS = ["binary_sensor", "select", "text", "update"]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Asyncronious entry setup."""
    _LOGGER.debug("Entry data: %s", entry.data)

    coordinator = OpenWRTDataCoordinator(
        hass, entry.data["devices"][0]["ip"], entry.data["devices"][0]["config_type"]
    )

    # Initial refresh — must be awaited here before loading platforms
    await coordinator.async_config_entry_first_refresh()

    # hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {"devices": entry.data.get("devices", [])}

    # for platform in PLATFORMS:
    #    hass.async_create_task(
    #        hass.config_entries.async_forward_entry_setups(entry, [platform])
    #    )
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Asynchronious entry unload."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok


async def async_get_options_flow(config_entry):
    """Asyncronious options flow."""
    return OpenWRTOptionsFlowHandler(config_entry)
