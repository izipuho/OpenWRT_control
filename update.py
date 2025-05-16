"""
This entity appears in Home Assistant and when triggered, it executes your remote script (e.g., sh /etc/openwrt-update.sh via SSH):
"""

from homeassistant.components.update import UpdateEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.const import STATE_UNKNOWN

from .const import DOMAIN, SSH_KEY_PATH
import paramiko

async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([OpenWRTUpdateEntity(coordinator, entry.entry_id)])

class OpenWRTUpdateEntity(CoordinatorEntity, UpdateEntity):
    def __init__(self, coordinator, entry_id):
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry_id}_update"
        self._attr_name = "OpenWRT Firmware Update"
        self.ip = coordinator.ip

    @property
    def installed_version(self):
        return self.coordinator.data.get("os_version", STATE_UNKNOWN)

    @property
    def latest_version(self):
        # Placeholder — you'd call your TOH parser script here
        return "PLACEHOLDER_VERSION"

    @property
    def available(self):
        return self.coordinator.data.get("online", False)

    async def async_install(self, version: str, backup: bool, **kwargs):
        await self.hass.async_add_executor_job(self._run_update)

    def _run_update(self):
        try:
            key = paramiko.Ed25519Key(filename=SSH_KEY_PATH)
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(self.ip, username="root", pkey=key, timeout=10)

            # Replace this command with your actual update script path
            ssh.exec_command("sh /etc/openwrt-update.sh")
            ssh.close()
        except Exception as e:
            print(f"Update trigger failed: {e}")

