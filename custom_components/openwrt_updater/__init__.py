"""Initialize OpenWRT Updater integration."""

import asyncio
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
        "⚙️OpenWRT Control: setup_entry id=%s source=%s title=%s",
        entry.entry_id,
        entry.source,
        entry.title,
    )

    entry.async_on_unload(entry.add_update_listener(_on_entry_update))

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
    if entry.unique_id == "__global__":
        hass.data[DOMAIN]["config"] = {}
        unload_ok = True
    else:
        unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
        if unload_ok:
            hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Reload entry."""
    await async_setup_entry(hass, entry)
    await async_unload_entry(hass, entry)
    return True


async def _on_entry_update(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload on any change; if global – обновить всех."""
    if entry.unique_id == "__global__":
        # reread global config
        hass.data[DOMAIN]["config"] = dict(entry.options or {})
        # reread all device-entries
        tasks = [
            hass.config_entries.async_reload(e.entry_id)
            for e in hass.config_entries.async_entries(DOMAIN)
            if e.entry_id != entry.entry_id and e.unique_id != "__global__"
        ]
        if tasks:
            await asyncio.gather(*tasks)
        return

    # reread only currenty entry
    await hass.config_entries.async_reload(entry.entry_id)
