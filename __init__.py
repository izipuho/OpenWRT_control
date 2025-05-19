from .const import DOMAIN

async def async_setup_entry(hass, entry):
    from .coordinator import OpenWRTDataUpdateCoordinator
    coordinator = OpenWRTDataUpdateCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

    hass.config_entries.async_setup_platforms(entry, ["sensor", "update"])
    return True

async def async_unload_entry(hass, entry):
    await hass.config_entries.async_unload_platforms(entry, ["sensor", "update"])
    hass.data[DOMAIN].pop(entry.entry_id)
    return True

