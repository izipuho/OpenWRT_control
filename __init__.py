from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.typing import ConfigType

from .const import DOMAIN
from .coordinator import OpenWRTDataUpdateCoordinator

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    coordinator = OpenWRTDataUpdateCoordinator(hass, entry.data)
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

    hass.config_entries.async_setup_platforms(entry, ["sensor", "update"])
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    await hass.config_entries.async_unload_platforms(entry, ["sensor", "update"])
    hass.data[DOMAIN].pop(entry.entry_id)
    return True

