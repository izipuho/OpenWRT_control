"""Options flow for OpenWRT Updater: add devices via UI."""

import logging

from homeassistant import config_entries

from .helpers import build_device_schema, upsert_device

_LOGGER = logging.getLogger(__name__)


class OpenWRTOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options for an existing config entry."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        self.config_entry = config_entry
        # Текущее состояние устройств из options
        _LOGGER.warning("Config entry: %s", config_entry)
        self._devices = dict(config_entry.options.get("devices", {}))

    async def async_step_init(self, user_input=None):
        """Entry point – сразу открываем форму добавления устройства."""
        _LOGGER.warning("Options flow: init")
        return await self.async_step_add_device()

    async def async_step_add_device(self, user_input=None):
        """Шаг добавления/редактирования устройства."""
        if user_input is not None:
            upsert_device(self._devices, user_input)

            if user_input.get("add_another"):
                # Цикл добавления ещё одного
                return await self.async_step_add_device()

            # Сохранить и выйти
            return self.async_create_entry(
                title="",  # заголовок игнорируется для options
                data={"devices": self._devices},
            )

        # Значения по умолчанию (пустые при открытии из options)
        defaults: dict = {}
        schema = await self.hass.async_add_executor_job(
            build_device_schema, self.hass, defaults
        )
        return self.async_show_form(step_id="add_device", data_schema=schema)
