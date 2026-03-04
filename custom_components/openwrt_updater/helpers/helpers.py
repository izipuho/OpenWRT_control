"""Shared helper utilities for config and diagnostics."""

import asyncio
import contextlib
import json
import logging
from pathlib import Path

import voluptuous as vol
import yaml

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


def load_device_option(
    entry: ConfigEntry, ip: str, key: str, default: str | None
) -> dict:
    """Load a value for a device from config entry options."""
    devices = entry.options.get("devices", {})
    return devices.get(ip, {}).get(key, default)


def save_device_option(
    hass: HomeAssistant | None, entry: ConfigEntry, ip: str, key: str, value: str
) -> None:
    """Save a value for a device into config entry options."""
    # Deep copy to avoid in-place mutation
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
    except yaml.YAMLError:
        _LOGGER.error("Error parsing YAML from %s", config_path)
    except Exception:
        _LOGGER.error("Unexpected error loading config from %s", config_path)


def build_global_options_schema(
    hass: HomeAssistant | None, defaults=None
) -> vol.Schema:
    """Build the global options schema."""
    return vol.Schema(
        {
            # vol.Optional("use_asu", default=defaults["use_asu"]): cv.boolean,
            vol.Optional("asu_base_url", default=defaults["asu_base_url"]): cv.string,
            vol.Optional(
                "download_base_url", default=defaults["download_base_url"]
            ): cv.string,
            vol.Optional(
                "builder_location",
                default=defaults["builder_location"],
            ): cv.string,
            vol.Optional("ssh_key_path", default=defaults["ssh_key_path"]): cv.string,
            # vol.Optional("toh_url", default=defaults["toh_url"]): cv.string,
            # vol.Optional(
            #    "config_types_file",
            #    default=defaults["config_types_file"],
            # ): cv.string,
            vol.Optional(
                "toh_timeout_hours",
                default=defaults["toh_timeout_hours"],
            ): int,
            vol.Optional(
                "device_timeout_minutes",
                default=defaults["device_timeout_minutes"],
            ): int,
            vol.Optional(
                "wifi_roaming_enabled",
                default=defaults.get("wifi_roaming_enabled", False),
            ): cv.boolean,
            vol.Optional(
                "wifi_roaming_mobility_domain",
                default=defaults.get("wifi_roaming_mobility_domain", ""),
            ): cv.string,
            vol.Optional(
                "wifi_roaming_ft_over_ds",
                default=defaults.get("wifi_roaming_ft_over_ds", False),
            ): cv.boolean,
            vol.Optional(
                "wifi_roaming_ft_psk_generate_local",
                default=defaults.get("wifi_roaming_ft_psk_generate_local", False),
            ): cv.boolean,
        }
    )


def build_wifi_policy_schema(defaults: dict | None = None) -> vol.Schema:
    """Build place/device wifi policy schema."""
    d = defaults or {}
    return vol.Schema(
        {
            vol.Required(
                "roaming_enabled",
                default=d.get("roaming_enabled", False),
            ): cv.boolean,
            vol.Optional(
                "mobility_domain",
                default=d.get("mobility_domain", ""),
            ): cv.string,
            vol.Required(
                "ft_over_ds",
                default=d.get("ft_over_ds", False),
            ): cv.boolean,
            vol.Required(
                "ft_psk_generate_local",
                default=d.get("ft_psk_generate_local", False),
            ): cv.boolean,
        }
    )


def build_device_schema(
    hass: HomeAssistant | None, defaults: dict | None
) -> vol.Schema:
    """Build the device options schema."""
    # config_types_path = (
    #    hass.data.get(DOMAIN, {}).get("config", {}).get("config_types_path", "")
    # )
    # config_types = load_config_types(config_types_path)
    # choices = sorted(config_types.keys())

    d = defaults or {}
    return vol.Schema(
        {
            vol.Required("ip", default=d.get("ip", "")): cv.string,
            # vol.Required(
            #    "config_type",
            #    default=d.get("config_type", choices[0] if choices else ""),
            # ): vol.In(choices),
            vol.Required("simple_update", default=d.get("simple_update", True)): bool,
            vol.Required("force_update", default=d.get("force_update", False)): bool,
            vol.Required(
                "wifi_policy_override",
                default=d.get("wifi_policy_override", False),
            ): bool,
            vol.Optional(
                "wifi_roaming_enabled",
                default=d.get("wifi_roaming_enabled", False),
            ): bool,
            vol.Optional(
                "wifi_roaming_mobility_domain",
                default=d.get("wifi_roaming_mobility_domain", ""),
            ): cv.string,
            vol.Optional(
                "wifi_roaming_ft_over_ds",
                default=d.get("wifi_roaming_ft_over_ds", False),
            ): bool,
            vol.Optional(
                "wifi_roaming_ft_psk_generate_local",
                default=d.get("wifi_roaming_ft_psk_generate_local", False),
            ): bool,
            vol.Optional("add_another", default=d.get("add_another", False)): bool,
        }
    )


def upsert_device(devices: dict, user_input: dict) -> dict:
    """Insert or update a device by IP and return the map."""
    ip = user_input["ip"]
    devices[ip] = {
        "ip": ip,
        # "config_type": user_input["config_type"],
        "simple_update": user_input["simple_update"],
        "force_update": user_input["force_update"],
    }
    if user_input.get("wifi_policy_override"):
        devices[ip]["wifi_policy"] = {
            "roaming_enabled": user_input.get("wifi_roaming_enabled", False),
            "mobility_domain": user_input.get("wifi_roaming_mobility_domain", ""),
            "ft_over_ds": user_input.get("wifi_roaming_ft_over_ds", False),
            "ft_psk_generate_local": user_input.get(
                "wifi_roaming_ft_psk_generate_local",
                False,
            ),
        }
    else:
        devices[ip].pop("wifi_policy", None)
    return devices



async def dump_toh_json(
    hass: HomeAssistant,
    data,
    filename: str = "toh_dump.json",
    to_config: bool = False,
) -> None:
    """Persist raw TOH JSON for debugging.

    If to_config=True -> writes to /config/<filename>.
    Else -> writes to the integration root (custom_components/openwrt_updater/<filename>).
    """
    try:
        if to_config:
            # Safer, always writable and visible from UI add-ons
            path = Path(hass.config.path(filename))
        else:
            # This module lives under custom_components/openwrt_updater/helpers/debug_dump.py
            # parents[1] -> custom_components/openwrt_updater
            path = Path(__file__).resolve().parents[1] / filename

        text = json.dumps(data, ensure_ascii=False, indent=2)

        def _write() -> None:
            """Write JSON dump to disk inside an executor thread."""
            path.write_text(text, encoding="utf-8")

        await hass.async_add_executor_job(_write)
        _LOGGER.warning("TOH dump saved to: %s", path)
    except Exception as exc:
        _LOGGER.error("Failed to dump TOH JSON: %s", exc)


async def async_check_alive(host: str, port: int = 22, timeout: float = 1.0) -> bool:
    """Run a fast TCP liveness check."""
    try:
        r, w = await asyncio.wait_for(
            asyncio.open_connection(host=host, port=port), timeout=timeout
        )
    except (TimeoutError, OSError) as err:
        _LOGGER.debug("Alive check for %s:%s failed: %s", host, port, err)
        return False
    except Exception as err:
        _LOGGER.debug("Unexpected error for %s:%s: %s", host, port, err)
        return False

    w.close()
    with contextlib.suppress(Exception):
        await w.wait_closed()
    return True
