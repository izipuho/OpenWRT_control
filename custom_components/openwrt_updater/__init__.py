"""Initialize OpenWRT Updater integration."""

import asyncio
from datetime import timedelta
import logging
from pathlib import Path

from homeassistant.config_entries import ConfigEntry, ConfigEntryNotReady
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .coordinators import OpenWRTDeviceCoordinator, TohCacheCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [
    "binary_sensor",
    # "button",
    "select",
    "switch",
    "text",
    "update",
]


async def async_setup(hass: HomeAssistant, config):
    """Set wait for global point."""
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN].setdefault("global_ready", asyncio.Event())
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up the integration: prepare shared TOH cache and per-device coordinators.

    Stores the following structure in hass.data[DOMAIN][entry.entry_id]:
      - "toh_coordinator": TohCacheCoordinator
      - "device_coordinators": dict[ip, OpenWRTDeviceCoordinator]
      - "devices_cfg": dict loaded from options
    """

    entry.async_on_unload(entry.add_update_listener(_on_entry_update))

    hass.data.setdefault(DOMAIN, {})

    # toh_coordinator = TohCacheCoordinator(hass, timedelta(hours=_DEFAULT_TOH_TIMEOUT))
    # await toh_coordinator.async_config_entry_first_refresh()
    # hass.data[DOMAIN]["toh_cache"] = toh_coordinator

    hass.data[DOMAIN].setdefault(entry.entry_id, {})

    if entry.unique_id == "__global__":
        component_config = dict(entry.options)

        ssh_key_path = hass.config.path(component_config.get("ssh_key_path"))
        config_types_path = str(
            Path(__file__).parent / component_config.get("config_types_file")
        )

        hass.data[DOMAIN]["config"] = component_config
        hass.data[DOMAIN]["config"]["ssh_key_path"] = ssh_key_path
        hass.data[DOMAIN]["config"]["config_types_path"] = config_types_path

        toh_coordinator = TohCacheCoordinator(
            hass, timedelta(hours=component_config["toh_timeout_hours"])
        )
        await toh_coordinator.async_config_entry_first_refresh()
        hass.data[DOMAIN]["toh_cache"] = toh_coordinator

        hass.data[DOMAIN]["global_ready"].set()
    else:
        if not hass.data[DOMAIN]["global_ready"].is_set():
            raise ConfigEntryNotReady("Waiting for __global__ entry")

        hass.data[DOMAIN][entry.entry_id]["data"] = entry.data

        # Get devices info from config_entry
        devices = entry.options.get("devices", [])

        # Save config-entry and coordinator data to hass.data for each device
        for ip, device in devices.items():
            # Config-entry data
            hass.data[DOMAIN][entry.entry_id][ip] = dict(device)
            # Coordinator data
            coordinator = OpenWRTDeviceCoordinator(hass, entry, ip)
            await coordinator.async_config_entry_first_refresh()
            hass.data[DOMAIN][entry.entry_id][ip]["coordinator"] = coordinator
            # hass.data[DOMAIN][entry.entry_id][ip].update(coordinator.data)

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
