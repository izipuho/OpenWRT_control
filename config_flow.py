import yaml
import logging

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult

from .const import DOMAIN, CONFIG_TYPES_PATH
import voluptuous as vol

_LOGGER = logging.getLogger(__name__)


async def _load_config_types(hass: HomeAssistant):
    try:
        path = hass.config.path(CONFIG_TYPES_PATH)
        with open(path, "r") as f:
            return yaml.safe_load(f)
    except Exception as e:
        _LOGGER.error("Failed to load config_types.yaml: %s", e)
        return {}


class OpenWRTConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None) -> FlowResult:
        errors = {}
        config_types = await self.hass.async_add_executor_job(lambda: None)

        if user_input is not None:
            # validate input and create entry
            return self.async_create_entry(title=user_input["ip"], data=user_input)

        config_types = await _load_config_types(self.hass)
        options = [(key, val["name"]) for key, val in config_types.items()]

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required("ip"): str,
                    vol.Required("config_type"): vol.In(dict(options)),
                }
            ),
            errors=errors,
        )

