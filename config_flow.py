import voluptuous as vol
from homeassistant import config_entries
from .const import DOMAIN
from .ssh_client import ssh_command

DEVICE_SCHEMA = vol.Schema({
    vol.Required("ip"): str,
    vol.Required("device_type"): str,
    vol.Required("os"): str,
    vol.Optional("key_path", default="/config/ssh/id_rsa"): str,
})

class OpenWRTConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    async def async_step_user(self, user_input=None):
        errors = {}
        if user_input is not None:
            ip = user_input["ip"]
            key_path = user_input.get("key_path")
            result = await self.hass.async_add_executor_job(
                ssh_command, ip, "echo ok", key_path
            )
            if "Error" not in result:
                return self.async_create_entry(title=ip, data=user_input)
            errors["base"] = "cannot_connect"

        return self.async_show_form(
            step_id="user", data_schema=DEVICE_SCHEMA, errors=errors
        )
