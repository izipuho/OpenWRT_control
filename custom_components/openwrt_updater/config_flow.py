"""Configuration flow description."""
# TODO prettify select (name instead code)
# TODO validate IP

import logging

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow

from .const import DOMAIN
from .helpers import build_device_schema, upsert_device
from .options_flow import OpenWRTOptionsFlowHandler

_LOGGER = logging.getLogger(__name__)


class OpenWRTConfigFlow(ConfigFlow, domain=DOMAIN):
    """Configuration flow class."""

    def __init__(self) -> None:
        """Initialize config flow class."""
        self.data = {}
        self.options = {}

    async def async_step_user(self, user_input=None):
        """Request place info."""
        if user_input is not None:
            self.data = {
                "place_name": user_input["place_name"],
                "place_ipmask": user_input["place_ipmask"],
            }
            return await self.async_step_add_device()

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required("place_name"): str,
                    vol.Required("place_ipmask"): str,
                }
            ),
        )

    async def async_step_add_device(self, user_input=None):
        """Request device info."""
        if user_input is not None:
            upsert_device(self.options, user_input)
            if user_input.get("add_another"):
                return await self.async_step_add_device()
            _LOGGER.debug("Create device with data: %s", user_input)
            return self.async_create_entry(
                title=f"OpenWRT updater {self.data['place_name']}",
                data=self.data,
                options={"devices": self.options},
            )

        defaults = {"ip": f"{self.data['place_ipmask']}."}
        schema = await self.hass.async_add_executor_job(
            build_device_schema, self.hass, defaults
        )
        return self.async_show_form(step_id="add_device", data_schema=schema)


async def async_get_options_flow(config_entry):
    """Return the options flow handler for this config entry."""
    return OpenWRTOptionsFlowHandler(config_entry)
