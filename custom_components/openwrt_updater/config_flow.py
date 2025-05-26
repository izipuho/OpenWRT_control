"""Configuration flow description."""

import logging

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow

from .config_loader import load_config_types
from .const import CONFIG_TYPES_PATH, DOMAIN

_LOGGER = logging.getLogger(__name__)


class OpenWRTConfigFlow(ConfigFlow, domain=DOMAIN):
    """Configuration flow class."""

    def __init__(self) -> None:
        """Initialize config flow class."""
        self.devices = []

    async def async_step_user(self, user_input=None):
        """Asyncronious user step."""
        config_types_path = self.hass.config.path(CONFIG_TYPES_PATH)
        config_types = await self.hass.async_add_executor_job(
            load_config_types, config_types_path
        )
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
