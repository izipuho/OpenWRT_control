"""
This reads available config types from config_types.yaml
Uses test_ssh_connection() from ssh_client.py to verify connectivity
Stores device IP as the unique ID
Uses async_get_options_flow() to support future options editing
"""

import yaml
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult

from .const import (
    DOMAIN,
    CONF_IP,
    CONF_CONFIG_TYPE,
    CONFIG_TYPES_FILE,
    SSH_KEY_PATH,
)
from .ssh_client import test_ssh_connection


def load_config_types():
    with open(CONFIG_TYPES_FILE, "r") as f:
        return yaml.safe_load(f)


class OpenWRTConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None) -> FlowResult:
        errors = {}
        config_types = load_config_types()
        config_type_names = [item["name"] for item in config_types]

        if user_input is not None:
            ip = user_input[CONF_IP]
            config_type = user_input[CONF_CONFIG_TYPE]

            success = await self.hass.async_add_executor_job(
                test_ssh_connection, ip
            )

            if success:
                await self.async_set_unique_id(ip)
                self._abort_if_unique_id_configured()

                return self.async_create_entry(
                    title=f"OpenWRT {ip}", data=user_input
                )
            else:
                errors["base"] = "cannot_connect"

        schema = vol.Schema({
            vol.Required(CONF_IP): str,
            vol.Required(CONF_CONFIG_TYPE): vol.In(config_type_names)
        })

        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        from .options_flow import OpenWRTOptionsFlow
        return OpenWRTOptionsFlow(config_entry)

