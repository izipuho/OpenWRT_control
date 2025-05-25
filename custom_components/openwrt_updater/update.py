from homeassistant.components.update import (
    UpdateEntity,
    UpdateEntityFeature,
    UpdateDeviceClass,
)
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from .coordinator import OpenWRTDataCoordinator
from .ssh_client import trigger_update
from .const import DOMAIN, KEY_PATH


class OpenWRTUpdateEntity(CoordinatorEntity, UpdateEntity):
    def __init__(self, coordinator, ip, update_callback):
        super().__init__(coordinator)
        self._ip = ip
        self._attr_name = f"Firmware Update ({ip})"
        self._attr_unique_id = f"{ip}_firmware"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, self._ip)},
            "name": f"OpenWRT {self._ip}",
            "manufacturer": "OpenWRT",
            "model": "Router",
        }
        self._update_callback = update_callback
        self._attr_supported_features = UpdateEntityFeature.INSTALL
        self._attr_device_class = UpdateDeviceClass.FIRMWARE

    @property
    def installed_version(self):
        return self.coordinator.data.get("current_os_version")

    @property
    def latest_version(self):
        return self.coordinator.data.get("available_os_version")

    @property
    def available(self):
        return self.coordinator.last_update_success

    @property
    def title(self):
        return f"OpenWRT {self._ip}"

    @property
    def entity_picture(self):
        return None

    async def async_install(self, version: str | None, backup: bool, **kwargs):
        await self._update_callback(self._ip)


async def async_setup_entry(hass, config_entry, async_add_entities):
    devices = config_entry.data.get("devices", [])
    ssh_key_path = hass.config.path(KEY_PATH)

    entities = []
    for device in devices:
        ip = device["ip"]
        config_type = device["config_type"]

        coordinator = OpenWRTDataCoordinator(hass, ip, config_type)

        async def update_callback(ip):
            await hass.async_add_executor_job(trigger_update, ip, ssh_key_path, True, coordinator.data.get("snapshot_url"))

        entities.extend(
            [
                OpenWRTUpdateEntity(coordinator, ip, update_callback),
            ]
        )

    async_add_entities(entities, update_before_add=True)


