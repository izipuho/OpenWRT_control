"""Configuration flow description."""
# TODO prettify select (name instead code)
# TODO validate IP

import logging

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.selector import (
    SelectSelector,
    SelectSelectorConfig,
    SelectOptionDict,
)

from .const import DOMAIN, INTEGRATION_DEFAULTS
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
        """Request for action."""
        if user_input is not None:
            _LOGGER.warning("User input for Step User: %s", user_input)
            action = user_input.get("action")
            if action == "global":
                return await self.async_step_global()
            return await self.async_step_add_place()

        schema = vol.Schema(
            {
                vol.Required("action", default="place"): SelectSelector(
                    SelectSelectorConfig(
                        options=["global", "add_place"], translation_key="action_choice"
                    )
                )
            }
        )
        return self.async_show_form(step_id="user", data_schema=schema)

    async def async_step_global(self, user_input=None):
        """Create global-entry."""
        # Пробуем зарезервировать уникальный ID глобального entry
        await self.async_set_unique_id("__global__", raise_on_progress=False)
        # Если уже есть — просто завершаем с abort (пользователь зайдет в «Настроить» на карточке)
        self._abort_if_unique_id_configured()

        if user_input is not None:
            # Заводим Global entry: data пустые, опции — глобальные настройки
            return self.async_create_entry(
                title="OpenWRT Control — Global config",
                data={},
                options=user_input,
            )
        schema = vol.Schema(
            {
                vol.Optional(
                    "master_node", default=INTEGRATION_DEFAULTS["master_node"]
                ): cv.string,
                vol.Optional(
                    "builder_location",
                    default=INTEGRATION_DEFAULTS["builder_location"],
                ): cv.string,
                vol.Optional(
                    "ssh_key_path", default=INTEGRATION_DEFAULTS["ssh_key_path"]
                ): cv.string,
                vol.Optional(
                    "TOH_url", default=INTEGRATION_DEFAULTS["TOH_url"]
                ): cv.string,
                vol.Optional(
                    "config_types_file",
                    default=INTEGRATION_DEFAULTS["config_types_file"],
                ): cv.string,
            }
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

    async def async_get_options_flow(self, config_entry):
        """Wire options flow for this entry."""
        _LOGGER.warning("Start Options flow handled")
        return OpenWRTOptionsFlowHandler(config_entry)
