"""
Reads the same config_types.yaml file
Lets users reconfigure the IP or config type of a device after adding it
Mirrors the initial config UI for consistency
"""

import yaml
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback

from .const import (
    DOMAIN,
    CONF_IP,
    CONF_CONFIG_TYPE,
    CONFIG_TYPES_FILE,
)

def load_config_types():
    with open(CONFIG_TYPES_FILE, "r") as f:
        return yaml.safe_load(f)

class OpenWRTOptionsFlow(config_entries.OptionsFlow):
    def __init__(self, config_entry):
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        errors = {}
        config_types = load_config_types()
        config_type_names = [item["name"] for item in config_types]

        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        current = self.config_entry.data
        schema = vol.Schema({
            vol.Required(CONF_IP, default=current.get(CONF_IP)): str,
            vol.Required(CONF_CONFIG_TYPE, default=current.get(CONF_CONFIG_TYPE)): vol.In(config_type_names),
        })

        return self.async_show_form(step_id="init", data_schema=schema, errors=errors)
