import logging

import voluptuous as vol
import yaml

from homeassistant.config_entries import ConfigFlow

from .const import CONFIG_TYPES_PATH, DOMAIN
from .config_loader import load_config_types

_LOGGER = logging.getLogger(__name__)


class OpenWRTConfigFlow(ConfigFlow, domain=DOMAIN):
    VERSION = 1

    def __init__(self):
        self.devices = []

    async def async_step_user(self, user_input=None):
        config_types_path = self.hass.config.path(CONFIG_TYPES_PATH)
        config_types = await self.hass.async_add_executor_job(load_config_types, config_types_path)
        errors = {}
        if user_input is not None:
            self.devices.append(user_input)
            if user_input.get("add_another"):
                return await self.async_step_user()
            _LOGGER.debug("Create device with data: %s", self.devices)
            return self.async_create_entry(
                title=f"OpenWRT updater {self.devices[0]['ip']}",
                data={"devices": self.devices},
            )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required("ip"): str,
                    vol.Required("config_type"): vol.In(sorted(config_types.keys())),
                    vol.Required("is_simple", default=True): bool,
                    vol.Optional("add_another", default=False): bool,
                }
            ),
            errors=errors,
        )


#    @staticmethod
#    @callback
#    def async_get_options_flow(config_entry):
#        return OpenWRTOptionsFlowHandler(config_entry)


# class OpenWRTOptionsFlowHandler(config_entries.OptionsFlow):
#    def __init__(self, config_entry):
#        self.config_entry = config_entry
#
#    async def _load_config_types(self):
#        def read_yaml():
#            path = self.hass.config.path(
#                "custom_components/openwrt_control/config_types.yaml"
#            )
#            with open(path, "r") as f:
#                return yaml.safe_load(f)
#
#        config_types = await self.hass.async_add_executor_job(read_yaml)
#        return {key: value.get("name", key) for key, value in config_types.items()}
#
#    async def async_step_init(self, user_input=None):
#        config_types = await self._load_config_types()
#
#        if user_input is not None:
#            return self.async_create_entry(title="", data=user_input)
#
#        return self.async_show_form(
#            step_id="init",
#            data_schema=vol.Schema(
#                {
#                    vol.Required(
#                        CONF_IP, default=self.config_entry.data.get(CONF_IP)
#                    ): str,
#                    vol.Required(
#                        CONF_CONFIG_TYPE,
#                        default=self.config_entry.data.get(CONF_CONFIG_TYPE),
#                    ): vol.In(config_types),
#                }
#            ),
#        )

