from homeassistant import config_entries
import voluptuous as vol
from .const import DOMAIN, CONF_CONFIG_TYPE
import yaml
import os

CONFIG_PATH = "/config/custom_components/openwrt_updater/config_types.yaml"

def load_config_types():
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, "r") as file:
            config = yaml.safe_load(file)
            return {entry["name"]: entry["id"] for entry in config}
    return {}

class OpenWRTOptionsFlowHandler(config_entries.OptionsFlow):
    def __init__(self, config_entry):
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        config_types = load_config_types()
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema({
                vol.Optional(CONF_CONFIG_TYPE, default=self.config_entry.data.get(CONF_CONFIG_TYPE)): vol.In(list(config_types.keys())),
            })
        )
