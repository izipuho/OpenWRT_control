"""Configuration flow description."""
##TODO prettify select (name instead code)
##TODO validate IP

import logging

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow

from .helpers import load_config_types
from .const import CONFIG_TYPES_PATH, DOMAIN

_LOGGER = logging.getLogger(__name__)


class OpenWRTConfigFlow(ConfigFlow, domain=DOMAIN):
    """Configuration flow class."""

    def __init__(self) -> None:
        """Initialize config flow class."""
        self.data = []
        self.options = {}

    async def async_step_user(self, user_input=None):
        """Asyncronious user step."""
        config_types_path = self.hass.config.path(CONFIG_TYPES_PATH)
        config_types = await self.hass.async_add_executor_job(
            load_config_types, config_types_path
        )
        errors = {}
        if user_input is not None:
            # self.devices[user_input["ip"]] = user_input
            # self.devices[user_input["ip"]] = {user_input}
            # self.data[user_input["ip"]] = {"ip": user_input["ip"]}
            self.data.append(user_input["ip"])
            self.options[user_input["ip"]] = {
                "ip": user_input["ip"],
                "config_type": user_input["config_type"],
                "simple_update": user_input["simple_update"],
                "force_update": user_input["force_update"],
            }
            if user_input.get("add_another"):
                return await self.async_step_user()
            _LOGGER.debug("Create device with data: %s", user_input)
            return self.async_create_entry(
                title=f"OpenWRT updater {user_input['ip']}",
                data={"devices": self.data},
                options={"devices": self.options},
            )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required("ip"): str,
                    vol.Required("config_type"): vol.In(sorted(config_types.keys())),
                    vol.Required("simple_update", default=True): bool,
                    vol.Required("force_update", default=False): bool,
                    vol.Optional("add_another", default=False): bool,
                }
            ),
            errors=errors,
        )
