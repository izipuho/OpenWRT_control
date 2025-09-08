"""Simple update declaration."""

import logging

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .asu_client import ASUClient
from .const import DOMAIN, get_device_info
from .coordinators.device import OpenWRTDeviceCoordinator

_LOGGER = logging.getLogger(__name__)


class OpenWRTButton(CoordinatorEntity, ButtonEntity):
    """OpenWRT simple update class."""

    def __init__(
        self,
        coordinator: OpenWRTDeviceCoordinator,
        config_entry: ConfigEntry,
        ip: str,
        name: str,
        key: str,
        entity_category: EntityCategory,
    ) -> None:
        """Initialize simple update class."""
        super().__init__(coordinator)

        # helpers
        self._key = key
        place_name = config_entry.data["place_name"]

        # device properties
        self._ip = ip
        self._name = name
        self._attr_device_info = get_device_info(place_name, self._ip)
        self._config_entry = config_entry

        # base entity properties
        self._attr_name = f"{name} ({self._ip})"
        self._attr_unique_id = f"{name.lower().replace(' ', '_')}_{self._ip}"
        self._attr_entity_category = entity_category

        # specific entity properties

        _LOGGER.debug("%r", self)

    async def async_press(self) -> None:
        """Handle button press."""
        await self.coordinator.async_request_refresh()
        # _LOGGER.error(
        #    "DEBUG coordinator data for %s: %s",
        #    self._ip,
        #    self.coordinator.data,
        # )
        dev_coord = self.coordinator.data
        base_url = "https://sysupgrade.openwrt.org/"
        client = ASUClient(base_url=base_url)
        _LOGGER.error("Coordinator: %s", dev_coord)
        req = await client.build_request(
            version=dev_coord["available_os_version"],
            target=dev_coord["target"],
            board_name=dev_coord["board_name"],
            packages=dev_coord["packages"],
            client_name="smth",
        )
        _LOGGER.warning("Build request: %s", req.get("request_hash"))
        res = await client.poll_build_request(request_hash=req.get("request_hash"))
        fw_url = f"{base_url}/store/{res.bin_dir}/{res.file_name}"
        _LOGGER.warning(
            "Build URL: %s/store/%s/%s", base_url, res.bin_dir, res.file_name
        )

    def __repr__(self):
        """Repesent the object."""
        repr_str = f"\nName: {self.name}"
        repr_str += f"\n\tCat: {self.entity_category}"
        return repr_str


async def async_setup_entry(hass: HomeAssistant, config_entry, async_add_entities):
    """Asyncronious entry setup."""
    devices = config_entry.options.get("devices", {})

    entities = []
    for ip in devices:
        coordinator = hass.data[DOMAIN][config_entry.entry_id][ip]["coordinator"]
        entities.extend(
            [
                OpenWRTButton(
                    coordinator=coordinator,
                    config_entry=config_entry,
                    ip=ip,
                    name="Debug",
                    key="debug",
                    entity_category=EntityCategory.DIAGNOSTIC,
                ),
            ]
        )

    async_add_entities(entities, update_before_add=True)
