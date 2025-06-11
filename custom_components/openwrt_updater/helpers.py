"""Shared helpers. Persist states. Load config types."""

# from homeassistant.exceptions import HomeAssistantError
import logging
from pathlib import Path

import yaml
from .const import DOMAIN

from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)


def load_device_option(entry, ip, key, default=None):
    """Load a value for a device from config entry options."""
    devices = entry.options.get("devices", {})
    return devices.get(ip, {}).get(key, default)


def save_device_option(hass: HomeAssistant, entry, ip, key, value):
    """Save a value for a device into config entry options."""
    # Deep copy to avoid in-place mutation
    # options = copy.deepcopy(entry.options)
    options = dict(entry.options)
    devices = dict(options.get("devices", {}))

    device = dict(devices.get(ip, {}))
    device[key] = value
    devices[ip] = device
    options["devices"] = devices
    _LOGGER.debug("Trying to save value %s for key %s", value, key)
    _LOGGER.debug("Saving options: %s", devices)
    hass.data[DOMAIN][entry.entry_id][ip][key] = value
    hass.config_entries.async_update_entry(entry, options=options)
    _LOGGER.debug("Saved values: %s", entry.options.get("devices", {}).get(ip, {}))


def load_config_types(config_path: str) -> dict:
    """Load configuration types from a YAML file."""
    config_path = Path(config_path)
    try:
        with config_path.open("r", encoding="utf-8") as file:
            return yaml.safe_load(file) or {}
    except FileNotFoundError:
        _LOGGER.debug("Configuration file not found: %s", config_path)
        return {}
    except yaml.YAMLError as err:
        _LOGGER.error("Error parsing YAML from %s: %s", config_path, err)
        # raise HomeAssistantError(f"Invalid YAML in {config_path}") from err
    except Exception as err:
        _LOGGER.error("Unexpected error loading config from %s: %s", config_path, err)
        # raise HomeAssistantError(f"Error loading config from {config_path}") from err
