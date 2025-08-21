"""Options flow for OpenWRT Updater: add devices via UI."""

import logging

from homeassistant import config_entries

from .helpers import build_device_schema, build_global_options_schema, upsert_device

_LOGGER = logging.getLogger(__name__)


class OpenWRTOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options for an existing config entry."""

    def __init__(self) -> None:
        """Initialize Options Flow handler."""
        # self.config_entry = config_entry
        # Current entry state
        self._data = {}
        self._devices = {}

    def get_fresh_data(self):
        """Get fresh data all the time."""
        entry = self.hass.config_entries.async_get_entry(self.config_entry.entry_id)
        return dict(entry.options or {})

    async def async_step_init(self, user_input=None):
        """Entry point."""
        _LOGGER.warning("Options flow: init")
        self._data = dict(self.config_entry.data)
        self._devices = dict(self.config_entry.options.get("devices", {}))
        if self.config_entry.unique_id == "__global__":
            return await self.async_step_global()
        return await self.async_step_add_device()

    async def async_step_global(self, user_input=None):
        """Global options step."""
        if user_input is not None:
            _LOGGER.warning("Saving data to global entry: %s", user_input)
            return self.async_create_entry(title="", data=user_input)
        saved_options = self.get_fresh_data()
        schema = await self.hass.async_add_executor_job(
            build_global_options_schema, self.hass, saved_options
        )
        return self.async_show_form(step_id="global", data_schema=schema)

    async def async_step_add_device(self, user_input=None):
        """Add device step."""
        if user_input is not None:
            upsert_device(self._devices, user_input)

            if user_input.get("add_another"):
                return await self.async_step_add_device()

            return self.async_create_entry(
                title="",
                data={"devices": self._devices},
            )

        defaults: dict = {"ip": f"{self._data.get('place_ipmask', '')}."}
        schema = await self.hass.async_add_executor_job(
            build_device_schema, self.hass, defaults
        )
        return self.async_show_form(step_id="add_device", data_schema=schema)
