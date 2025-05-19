import voluptuous as vol
from homeassistant import config_entries
from .const import DOMAIN, CONF_IP, CONF_CONFIG_TYPE
import yaml
import os

CONFIG_PATH = "/config/custom_components/openwrt_updater/config_types.yaml"

def load_config_types():
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, "r") as file:
            config = yaml.safe_load(file)
            return {entry["name"]: entry["id"] for entry in config}
    return {}

class OpenWRTConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        config_types = load_config_types()
        if user_input is not None:
            return self.async_create_entry(title=user_input[CONF_IP], data=user_input)

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required(CONF_IP): str,
                vol.Required(CONF_CONFIG_TYPE): vol.In(list(config_types.keys())),
            })
        )
