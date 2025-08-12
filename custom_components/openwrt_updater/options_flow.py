"""Add devices on options flow."""

import ipaddress

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback

from .helpers import build_device_schema, upsert_device


def _validate_ip(ip_str: str) -> str:
    try:
        ipaddress.ip_address(ip_str)
    except ValueError as e:
        raise vol.Invalid("Invalid IP address") from e
    else:
        return ip_str


class OpenWRTOptionsFlowHandler(config_entries.OptionsFlow):
    """Options flow that mirrors config_flow.add_device."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry
        self._devices = dict(config_entry.options.get("devices", {}))

    async def async_step_init(self, user_input=None):
        """Entry point – go straight to add device form."""
        return await self.async_step_add_device()

    async def async_step_add_device(self, user_input=None):
        """Add device step."""
        if user_input is not None:
            upsert_device(self._devices, user_input)

            if user_input.get("add_another"):
                # loop to add the next device
                return await self.async_step_add_device()

            # save and exit
            return self.async_create_entry(
                title="",  # HA ignores title for options
                data={"devices": self._devices},
            )

        # defaults for convenience if editing/adding
        defaults = {}
        schema = await self.hass.async_add_executor_job(
            build_device_schema, self.hass, defaults
        )
        return self.async_show_form(step_id="add_device", data_schema=schema)

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Unobligatory call."""
        # unobligatory, but harmless
        return OpenWRTOptionsFlowHandler(config_entry)
