"""Updater entity declaration."""

import logging
import subprocess

from homeassistant.components.update import (
    UpdateDeviceClass,
    UpdateEntity,
    UpdateEntityFeature,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, KEY_PATH, get_device_info
from .coordinator import OpenWRTDataCoordinator
from .ssh_client import _connect_ssh

_LOGGER = logging.getLogger(__name__)


def trigger_update(
    hass: HomeAssistant,
    entry_id,
    device: dict,
    key_path: str,
):
    """Trigger update of the remote device."""
    _LOGGER.debug("Updating device: %s", device)
    ip = device["ip"]
    _LOGGER.debug("Updating device with HAss data: %s", hass.data[DOMAIN][entry_id][ip])
    is_simple = hass.data[DOMAIN][entry_id][ip]["simple_update"]
    is_force = hass.data[DOMAIN][entry_id][ip]["force_update"]
    if is_simple:
        url = hass.data[DOMAIN][entry_id][ip]["snapshot_url"]
        try:
            _LOGGER.debug("Trying to simple update %s", ip)
            _LOGGER.debug("Downloading %s", url)
            update_command = f"curl {url} --output /tmp/owrt.bin"
            if is_force:
                update_command += " && sysupgrade -v /tmp/owrt.bin"
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
        updater_location = "/home/zip/OpenWrt-builder"
        config_type = hass.data[DOMAIN][entry_id][ip]["config_type"]
        update_strategy = "install" if is_force else "copy"
        update_command = (
            f"cd {updater_location} && make C={config_type} HOST={ip} {update_strategy}"
        )
        master_node = "zip@10.8.25.20"
        try:
            _LOGGER.debug("Trying to update %s with %s.", ip, update_command)
            master = _connect_ssh(master_node.split("@")[1], key_path, username=master_node.split("@")[0])
            stdin, update, stderr = master.exec_command(update_command)
            output = update.read().decode().strip()
            _LOGGER.debug("Update result: %s", output)
        except Exception as e:
            _LOGGER.error("Failed to run update script: %s", e)
            return None
        else:
            return output.returncode


class OpenWRTUpdateEntity(CoordinatorEntity, UpdateEntity):
    """Updater entity declaration."""

    def __init__(self, coordinator, device, update_callback) -> None:
        """Initialize updater entity."""
        super().__init__(coordinator)
        # helpers
        self.device = device

        # device properties
        self._ip = device["ip"]
        self._attr_device_info = get_device_info(self._ip)

        # base entity properties
        self._attr_name = f"Firmware ({self._ip})"
        self._attr_unique_id = f"firmware_{self._ip}"

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
        return self.coordinator.data.get("current_os_version")

    @property
    def latest_version(self):
        """Return available version."""
        if self.coordinator.data is None:
            return "unavailable"
        return self.coordinator.data.get("available_os_version")

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
        await self._update_callback(self.coordinator.config_entry.entry_id, self.device)
        await self.coordinator.async_request_refresh()

    def __repr__(self):
        """Represent the object."""
        repr_str = f"\nName: {self.name}"
        repr_str += f"\n\tValue: {self._attr_latest_version}"
        return repr_str


async def async_setup_entry(hass: HomeAssistant, config_entry, async_add_entities):
    """Asyncronious entry setup."""
    devices = config_entry.options.get("devices", [])
    ssh_key_path = hass.config.path(KEY_PATH)

    entities = []

    async def update_callback(entry_id, device):
        await hass.async_add_executor_job(
            trigger_update, hass, entry_id, device, ssh_key_path
        )

    for ip, device in devices.items():
        coordinator = OpenWRTDataCoordinator(hass, ip)
        entities.extend(
            [
                OpenWRTUpdateEntity(coordinator, device, update_callback),
            ]
        )

    async_add_entities(entities, update_before_add=True)
