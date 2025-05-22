from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .coordinator import OpenWRTDataCoordinator  # Your coordinator class
import logging

_LOGGER = logging.getLogger(__name__)

PLATFORMS = ["text", "binary_sensor", "update", "select"]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
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
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok

