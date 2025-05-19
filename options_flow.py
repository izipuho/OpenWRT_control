import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback

from .const import DOMAIN, CONF_IP, CONF_CONFIG_TYPE
from .config_flow import load_config_types


class OpenWRTOptionsFlow(config_entries.OptionsFlow):
    def __init__(self, config_entry):
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        errors = {}
        config_types = load_config_types()
        config_type_names = [item["name"] for item in config_types]

        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        schema = vol.Schema({
            vol.Required(CONF_IP, default=self.config_entry.data.get(CONF_IP)): str,
            vol.Required(CONF_CONFIG_TYPE, default=self.config_entry.data.get(CONF_CONFIG_TYPE)): vol.In(config_type_names),
        })

        return self.async_show_form(step_id="init", data_schema=schema, errors=errors)
