"""Updater entity declaration."""
# TODO Turn on simple update. Now it only copies firmware and I guess it's wrong one.

import logging
import subprocess

from homeassistant.components.update import (
    UpdateDeviceClass,
    UpdateEntity,
    UpdateEntityFeature,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import KEY_PATH, get_device_info
from .coordinator import OpenWRTDataCoordinator
from .ssh_client import _connect_ssh

_LOGGER = logging.getLogger(__name__)


def trigger_update(
    hass: HomeAssistant,
    device: dict,  # ip: str,
    key_path: str,
):
    """Trigger update of the remote device."""
    ip = device["ip"]
    is_simple = device.get("simple_update", True)
    is_force = device.get("force_update", False)
    if is_simple:
        url_entity = f"text.snapshot_url_{ip.replace('.', '_')}"
        url = hass.states.get(url_entity).state
        try:
            _LOGGER.warning("Trying to simple update %s", ip)
            # update_command = f'echo "{ip}. Simple update: {is_simple}. URL: {url}" > /tmp/integration_test'
            update_command = f"curl {url} --output /tmp/owrt.bin"
            if is_force:
                update_command += " && mv /tmp/owrt.bin /tmp/ooooooo.bin"
            client = _connect_ssh(ip, key_path)
            stdin, stdout, stderr = client.exec_command(update_command)
            output = stdout.read().decode().strip()
            client.close()
        except Exception as e:
            _LOGGER.error("Failed to run update script: %s", e)
            return None
        else:
            return output
    else:
        config_type = device["config_type"]
        update_command = f"cd /home/zip/OpenWrt-builder && make C={config_type} {'install' if is_force else 'copy'}"
        master_node = "zip@10.8.25.20"
        try:
            ssh_command = ["ssh", "-A", master_node, update_command]
            output = subprocess.run(ssh_command, check=True)
        except Exception as e:
            _LOGGER.error("Failed to run update script: %s", e)
            return None
        else:
            return output.returncode


class OpenWRTUpdateEntity(CoordinatorEntity, UpdateEntity):
    """Updater entity declaration."""

    def __init__(self, coordinator, ip, update_callback) -> None:
        """Initialize updater entity."""
        super().__init__(coordinator)
        # helpers
        self.entry = coordinator.config_entry
        self.devices = self.entry.data.get("devices", [])
        self.device = next((d for d in self.devices if d.get("ip") == ip), {})
        # device properties
        self._ip = ip
        self._attr_device_info = get_device_info(ip)

        # base entity properties
        self._attr_name = f"Firmware ({ip})"
        self._attr_unique_id = f"firmware_{ip}"

        # specific entity properties
        self._update_callback = update_callback
        self._attr_supported_features = UpdateEntityFeature.INSTALL
        self._attr_device_class = UpdateDeviceClass.FIRMWARE
        self._attr_extra_state_attributes = {"force": False}

        _LOGGER.debug(repr(self))

    @property
    def installed_version(self):
        """Return installed version."""
        if self.coordinator.data is None:
            return "unavailable"
        return self.coordinator.data.get(self._ip).get("current_os_version")

    @property
    def latest_version(self):
        """Return available version."""
        if self.coordinator.data is None:
            return "unavailable"
        return self.coordinator.data.get(self._ip).get("available_os_version")

    @property
    def available(self):
        """Return availability."""
        return self.coordinator.last_update_success

    @property
    def entity_picture(self):
        """Do not try to override picture."""
        return None

    async def async_install(self, version: str | None, backup: bool, **kwargs):
        """Call update function."""
        await self._update_callback(self.device)

    def __repr__(self):
        """Represent the object."""
        repr_str = f"\nName: {self.name}"
        return repr_str


async def async_setup_entry(hass: HomeAssistant, config_entry, async_add_entities):
    """Asyncronious entry setup."""
    devices = config_entry.data.get("devices", [])
    ssh_key_path = hass.config.path(KEY_PATH)
    coordinator = OpenWRTDataCoordinator(hass, config_entry)

    entities = []

    async def update_callback(device):
        def get_is_simple(entity_id: str) -> bool:
            update_type_entity_state = hass.states.get(entity_id).state
            return {"on": True, "off": False}.get(update_type_entity_state.lower())

        await hass.async_add_executor_job(trigger_update, hass, device, ssh_key_path)

    for device in devices:
        entities.extend(
            [
                OpenWRTUpdateEntity(coordinator, device["ip"], update_callback),
            ]
        )

    async_add_entities(entities, update_before_add=True)
