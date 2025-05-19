from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entry_platform import async_forward_entry_setups, async_unload_platforms

from .const import DOMAIN

PLATFORMS = ["sensor"]

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = entry.data
    await async_forward_entry_setups(hass, entry, PLATFORMS)
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    await async_unload_platforms(hass, entry, PLATFORMS)
    hass.data[DOMAIN].pop(entry.entry_id)
    return True

