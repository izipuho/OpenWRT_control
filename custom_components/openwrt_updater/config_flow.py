"""Config flow for OpenWRT Updater."""

import logging

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow
from homeassistant.core import callback

from .helpers.const import DOMAIN, INTEGRATION_DEFAULTS
from .helpers.helpers import (
    build_device_base_schema,
    build_device_wifi_schema,
    build_global_options_schema,
    upsert_device,
)

_LOGGER = logging.getLogger(__name__)


class OpenWRTConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle the integration config flow."""

    def __init__(self) -> None:
        """Initialize the config flow."""
        self.data = {}
        self.options = {}
        self._pending_device = {}

    def check_global_exists(self) -> bool:
        """Return whether the global entry already exists."""
        return any(e.unique_id == "__global__" for e in self._async_current_entries())

    async def async_step_user(self, user_input=None):
        """Route to either the global step or add-place step."""
        if not self.check_global_exists():
            return await self.async_step_global()
        return await self.async_step_add_place()

    async def async_step_global(self, user_input=None):
        """Create the global config entry."""
        # Trying to reserve __global__ unique ID
        await self.async_set_unique_id("__global__", raise_on_progress=False)
        # Abort if already exists
        self._abort_if_unique_id_configured()

        if user_input is not None:
            return self.async_create_entry(
                title="OpenWRT Control — Global config",
                data={},
                options=user_input,
            )
        schema = await self.hass.async_add_executor_job(
            build_global_options_schema, self.hass, INTEGRATION_DEFAULTS
        )
        return self.async_show_form(step_id="global", data_schema=schema)

    async def async_step_add_place(self, user_input=None):
        """Collect place-level information."""
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
        """Collect device-level information."""
        if user_input is not None:
            self._pending_device = dict(user_input)
            if user_input.get("wifi_policy_override"):
                return await self.async_step_add_device_wifi()
            return await self._async_finalize_device(self._pending_device)

        defaults = {"ip": f"{self.data['place_ipmask']}."}
        schema = await self.hass.async_add_executor_job(
            build_device_base_schema, self.hass, defaults
        )
        return self.async_show_form(step_id="add_device", data_schema=schema)

    async def async_step_add_device_wifi(self, user_input=None):
        """Collect Wi-Fi override settings for a device."""
        if user_input is not None:
            merged = {**self._pending_device, **user_input}
            return await self._async_finalize_device(merged)

        schema = await self.hass.async_add_executor_job(
            build_device_wifi_schema, {}
        )
        return self.async_show_form(step_id="add_device_wifi", data_schema=schema)

    async def _async_finalize_device(self, device_input: dict):
        """Store collected device options and continue flow."""
        upsert_device(self.options, device_input)
        if device_input.get("add_another"):
            self._pending_device = {}
            return await self.async_step_add_device()
        _LOGGER.debug("Create device with data: %s", device_input)
        self._pending_device = {}
        return self.async_create_entry(
            title=f"OpenWRT updater {self.data['place_name']}",
            data=self.data,
            options={"devices": self.options},
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Return the options flow handler for this entry."""
        from .options_flow import OpenWRTOptionsFlowHandler

        return OpenWRTOptionsFlowHandler()
