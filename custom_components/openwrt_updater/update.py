"""Updater entity declaration."""

import logging

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
    ip: str,
    key_path: str,
    is_simple: bool = True,
):
    """Trigger update of the remote device."""
    if is_simple:
        url_entity = f"text.snapshot_url_{ip.replace('.', '_')}"
        url = hass.states.get(url_entity).state
        try:
            update_command = f'echo "{ip}. Simple update: {is_simple}. URL: {url}" > /tmp/integration_test'
            # update_command = (
            #    f"curl {url} --output /tmp/o.bin && mv /tmp/o.bin /tmp/owrt.bin"
            # )
            # _LOGGER.info("Trying to update %s with %s", ip, update_command)
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
        config_type_entity = f"select.config_type_{ip.replace('.', '_')}"
        _LOGGER.warning("Trying to get state of %s", config_type_entity)
        config_type = hass.states.get(config_type_entity).state
        try:
            update_command = f'echo "{ip}. Simple update: {is_simple}. Config: {config_type}" > /tmp/integration_test'
            # client = _connect_ssh("10.8.25.20", key_path, username="zip")
            client = _connect_ssh(ip, key_path)
            stdin, stdout, stderr = client.exec_command(update_command)
            output = stdout.read().decode().strip()
            client.close()
            # _LOGGER.info("Trying to update %s", ip)
        except Exception as e:
            _LOGGER.error("Failed to run update script: %s", e)
            return None
        else:
            return output


class OpenWRTUpdateEntity(CoordinatorEntity, UpdateEntity):
    """Updater entity declaration."""

    def __init__(self, coordinator, ip, update_callback) -> None:
        """Initialize updater entity."""
        super().__init__(coordinator)
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

        _LOGGER.debug(repr(self))

    @property
    def installed_version(self):
        """Return installed version."""
        return self.coordinator.data.get("current_os_version")

    @property
    def latest_version(self):
        """Return available version."""
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
        await self._update_callback(self._ip)

    def __repr__(self):
        """Represent the object."""
        repr_str = f"\nName: {self.name}"
        return repr_str


async def async_setup_entry(hass: HomeAssistant, config_entry, async_add_entities):
    """Asyncronious entry setup."""
    devices = config_entry.data.get("devices", [])
    ssh_key_path = hass.config.path(KEY_PATH)

    entities = []
    for device in devices:
        ip = device["ip"]
        config_type = device["config_type"]

        coordinator = OpenWRTDataCoordinator(hass, config_entry, ip, config_type)

        async def update_callback(ip, config_type: str = config_type):
            def get_is_simple(entity_id: str) -> bool:
                update_type_entity_state = hass.states.get(entity_id).state
                return {"on": True, "off": False}.get(update_type_entity_state.lower())

            update_type_entity_id = f"switch.simple_update_{ip.replace('.', '_')}"

            await hass.async_add_executor_job(
                trigger_update,
                hass,
                ip,
                ssh_key_path,
                get_is_simple(update_type_entity_id),
            )

        entities.extend(
            [
                OpenWRTUpdateEntity(coordinator, ip, update_callback),
            ]
        )

    async_add_entities(entities, update_before_add=True)
