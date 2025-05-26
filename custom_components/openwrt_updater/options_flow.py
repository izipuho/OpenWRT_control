import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from .const import DOMAIN
import ipaddress


def validate_ip(ip_str):
    try:
        ipaddress.ip_address(ip_str)
        return ip_str
    except ValueError:
        raise vol.Invalid("Invalid IP address")


class OpenWRTOptionsFlowHandler(config_entries.OptionsFlow):
    def __init__(self, config_entry):
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        if user_input is not None:
            # Get current devices list
            devices = (
                self.config_entry.options.get("devices", [])
                if self.config_entry.options
                else []
            )

            new_device = {
                "ip": user_input["ip"],
                "config_type": user_input["config_type"],
            }

            devices.append(new_device)

            return self.async_create_entry(title="", data={"devices": devices})

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required("ip"): vol.All(str, validate_ip),
                    vol.Required("config_type"): str,
                }
            ),
        )
