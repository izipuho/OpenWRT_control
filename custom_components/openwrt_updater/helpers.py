"""Shared helpers. Persist states. Load config types."""

import logging
from pathlib import Path

import voluptuous as vol
import yaml

from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv

from .const import DOMAIN

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


def build_global_options_schema(hass, defaults=None):
    """Unified global options schema."""
    return vol.Schema(
        {
            vol.Optional("master_node", default=defaults["master_node"]): cv.string,
            vol.Optional(
                "builder_location",
                default=defaults["builder_location"],
            ): cv.string,
            vol.Optional("ssh_key_path", default=defaults["ssh_key_path"]): cv.string,
            vol.Optional("toh_url", default=defaults["TOH_url"]): cv.string,
            vol.Optional(
                "config_types_file",
                default=defaults["config_types_file"],
            ): cv.string,
        }
    )


def build_device_schema(hass, defaults=None):
    """Unified device add schema."""
    config_types_path = (
        hass.data.get(DOMAIN, {}).get("config", {}).get("config_types_path", "")
    )
    config_types = load_config_types(config_types_path)
    choices = sorted(config_types.keys())

    d = defaults or {}
    return vol.Schema(
        {
            vol.Required("ip", default=d.get("ip", "")): str,
            vol.Required(
                "config_type",
                default=d.get("config_type", choices[0] if choices else ""),
            ): vol.In(choices),
            vol.Required("simple_update", default=d.get("simple_update", True)): bool,
            vol.Required("force_update", default=d.get("force_update", False)): bool,
            vol.Optional("add_another", default=d.get("add_another", False)): bool,
        }
    )


def upsert_device(devices: dict, user_input: dict) -> dict:
    """Upsert device by ip and return values."""
    ip = user_input["ip"]
    devices[ip] = {
        "ip": ip,
        "config_type": user_input["config_type"],
        "simple_update": user_input["simple_update"],
        "force_update": user_input["force_update"],
    }
    return devices
