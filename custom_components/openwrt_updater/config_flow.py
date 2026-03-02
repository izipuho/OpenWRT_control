"""Configuration flow description."""

import logging

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow
from homeassistant.core import callback

from .presets.const import DOMAIN, INTEGRATION_DEFAULTS
from .helpers.helpers import (
    build_device_schema,
    build_global_options_schema,
    upsert_device,
)
from .options_flow import OpenWRTOptionsFlowHandler

_LOGGER = logging.getLogger(__name__)


class OpenWRTConfigFlow(ConfigFlow, domain=DOMAIN):
    """Configuration flow class."""

    def __init__(self) -> None:
        """Initialize config flow class."""
        self.data = {}
        self.options = {}

    def check_global_exists(self) -> bool:
        """Check for global entry."""
        return any(e.unique_id == "__global__" for e in self._async_current_entries())

    async def async_step_user(self, user_input=None):
        """Route for correct action: set globals or add place."""
        if not self.check_global_exists():
            return await self.async_step_global()
        return await self.async_step_add_place()

    async def async_step_global(self, user_input=None):
        """Create global entry."""
        # Trying to reserve __global__ unique ID
        await self.async_set_unique_id("__global__", raise_on_progress=False)
        # Abort if already exists
        self._abort_if_unique_id_configured()

        if user_input is not None:
            options = {"config": dict(user_input), "lists": {}, "profiles": {}}
            return self.async_create_entry(
                title="OpenWRT Control — Global config",
                data={},
                options=options,
            )
        schema = await self.hass.async_add_executor_job(
            build_global_options_schema, self.hass, INTEGRATION_DEFAULTS
        )
        return self.async_show_form(step_id="global", data_schema=schema)

    async def async_step_add_place(self, user_input=None):
        """Request place info."""
        if user_input is not None:
            self.data = {
                "place_name": user_input["place_name"],
                "place_ipmask": user_input["place_ipmask"],
            }
            return await self.async_step_add_device()

        return self.async_show_form(
            step_id="add_place",
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

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Wire options flow for this entry."""

        return OpenWRTOptionsFlowHandler()
