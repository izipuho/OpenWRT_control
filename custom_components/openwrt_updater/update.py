"""Updater entity declaration."""

import logging

from homeassistant.components.update import (
    UpdateDeviceClass,
    UpdateEntity,
    UpdateEntityFeature,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, get_device_info
from .ssh_client import OpenWRTSSH

_LOGGER = logging.getLogger(__name__)


async def trigger_update(
    hass: HomeAssistant,
    entry_id,
    ip: str,
    key_path: str,
):
    """Trigger update of the remote device."""
    conf = hass.data.get(DOMAIN, {}).get("config", {})
    _LOGGER.debug("Updating device with HAss data: %s", hass.data[DOMAIN][entry_id][ip])
    firmware_file = hass.data[DOMAIN][entry_id][ip]["coordinator"].data["firmware_file"]
    is_simple = hass.data[DOMAIN][entry_id][ip]["simple_update"]
    is_force = hass.data[DOMAIN][entry_id][ip]["force_update"]
    available_os_version = hass.data[DOMAIN][entry_id][ip]["coordinator"].data[
        "available_os_version"
    ]
    if firmware_file and is_force:
        _LOGGER.debug("Trying to update %s with local file %s", ip, firmware_file)
        async with OpenWRTSSH(ip, key_path) as client:
            return await client.exec_command(f"sysupgrade -v {firmware_file}")
    if is_simple:
        url = hass.data[DOMAIN][entry_id][ip]["coordinator"].data["snapshot_url"]
        try:
            _LOGGER.debug("Trying to simple update %s", ip)
            _LOGGER.debug("Downloading %s", url)
            update_command = (
                f"curl {url} --output /tmp/openwrt-{available_os_version}.bin"
            )
            if is_force:
                update_command += (
                    f" && sysupgrade -v /tmp/openwrt-{available_os_version}.bin"
                )
            async with OpenWRTSSH(ip, key_path) as client:
                output = await client.exec_command(update_command)
            _LOGGER.debug("Update result: %s", output)
        except Exception as e:
            _LOGGER.error("Failed to run update script: %s", e)
            return None
        else:
            return output
    else:
        builder_location = conf["builder_location"]
        config_type = hass.data[DOMAIN][entry_id][ip]["config_type"]
        update_strategy = "install" if is_force else "copy"
        update_command = f"cd {builder_location} && make C={config_type} HOST={ip} RELEASE={available_os_version} {update_strategy}"
        master_node = conf["master_node"].split("@")
        try:
            _LOGGER.debug("Trying to update %s with %s", ip, update_command)
            async with OpenWRTSSH(
                ip=master_node[1],
                key_path=key_path,
                username=master_node[0],
            ) as master:
                output = await master.exec_command(update_command)
            _LOGGER.debug("Update result: %s", output)
        except Exception as e:
            _LOGGER.error("Failed to run update script: %s", e)
            return None
        else:
            return output


class OpenWRTUpdateEntity(CoordinatorEntity, UpdateEntity):
    """Updater entity declaration."""

    def __init__(self, config_entry, coordinator, device, update_callback) -> None:
        """Initialize updater entity."""
        super().__init__(coordinator)
        # helpers
        self.device = device
        self.config_entry = config_entry

        # device properties
        self._ip = device["ip"]
        self._attr_device_info = get_device_info(self.device["place_name"], self._ip)

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
        await self._update_callback(self.config_entry.entry_id, self._ip)
        await self.coordinator.async_request_refresh()

    def __repr__(self):
        """Represent the object."""
        repr_str = f"\nName: {self.name}"
        repr_str += f"\n\tValue: {self._attr_latest_version}"
        return repr_str


async def async_setup_entry(hass: HomeAssistant, config_entry, async_add_entities):
    """Asyncronious entry setup."""
    place_name = config_entry.data["place_name"]
    devices = config_entry.options.get("devices", {})
    ssh_key_path = hass.data.get(DOMAIN, {}).get("config", {}).get("ssh_key_path", "")

    entities = []

    async def update_callback(entry_id, ip):
        await trigger_update(hass, entry_id, ip, ssh_key_path)

    for ip, device in devices.items():
        device["place_name"] = place_name
        coordinator = hass.data[DOMAIN][config_entry.entry_id][ip]["coordinator"]
        entities.extend(
            [
                OpenWRTUpdateEntity(config_entry, coordinator, device, update_callback),
            ]
        )

    async_add_entities(entities, update_before_add=True)
