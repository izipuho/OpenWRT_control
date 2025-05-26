"""Provide functions for load config types from YAML."""

import logging
from pathlib import Path

import yaml

from homeassistant.exceptions import HomeAssistantError

_LOGGER = logging.getLogger(__name__)


def load_config_types(config_path: str) -> dict:
    """Load configuration types from a YAML file."""
    config_path = Path(config_path)
    try:
        with config_path.open("r", encoding="utf-8") as file:
            return yaml.safe_load(file) or {}
    except FileNotFoundError:
        _LOGGER.warning("Configuration file not found: %s", config_path)
        return {}
    except yaml.YAMLError as err:
        _LOGGER.error("Error parsing YAML from %s: %s", config_path, err)
        raise HomeAssistantError(f"Invalid YAML in {config_path}") from err
    except Exception as err:
        _LOGGER.exception("Unexpected error loading config from %s", config_path)
        raise HomeAssistantError(f"Error loading config from {config_path}") from err
