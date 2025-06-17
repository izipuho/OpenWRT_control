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
                    vol.Optional("TOH_url", default="https://openwrt.org/toh.json"): cv.string,
                    vol.Optional("config_types_path", default="/config/custom_components/openwrt_updater/config_types.yaml"): cv.string,
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
    """Save YAML configuration to hass.data."""
    # Get config from configuration.yaml
    yaml_conf = config.get(DOMAIN, {})

    # Save it to hass.data[DOMAIN]
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN]["config"] = yaml_conf

    return True

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up config entry."""
    _LOGGER.debug(
        "Entry data init: %s\nEntry options init: %s", entry.data, entry.options
    )

    # Create empty config-entry dict
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {}

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

        _LOGGER.debug("Initial HAss data: %s", hass.data[DOMAIN][entry.entry_id][ip])

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
