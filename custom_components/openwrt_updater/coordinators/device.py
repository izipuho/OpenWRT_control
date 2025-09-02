"""Device coordinator that merges SSH state with cached TOH info."""

from __future__ import annotations

from datetime import timedelta
import logging
from typing import TYPE_CHECKING, Any

from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from ..const import DOMAIN
from ..helpers import load_config_types
from ..ssh_client import OpenWRTSSH
from ..types import DeviceData

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)
_DEVICE_SCAN_INTERVAL = timedelta(minutes=10)


class OpenWRTDeviceCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Polls device state over SSH and enriches it with TOH cache.

    This coordinator must not perform any network calls to TOH. It reads TOH
    information via the shared TohCacheCoordinator instance stored in hass.data.
    """

    def __init__(
        self, hass: HomeAssistant | None, config_entry: ConfigEntry, ip: str
    ) -> None:
        """Initialize the device coordinator for a specific IP."""
        super().__init__(
            hass=hass,
            logger=_LOGGER,
            name=f"{DOMAIN}-device-{ip}",
            update_interval=_DEVICE_SCAN_INTERVAL,
        )
        self.hass = hass
        self.entry = config_entry
        self.ip = ip

    async def _async_update_data(self) -> DeviceData:
        """Fetch device state and compose a DeviceData snapshot.

        - Live device state is fetched via `get_dev_state()`.
        - TOH info is resolved from the shared TohCacheCoordinator (no network).
        """
        config_types_path = self.hass.data[DOMAIN]["config"]["config_types_path"]
        config_types = await self.hass.async_add_executor_job(
            load_config_types, config_types_path
        )
        config_type = self.hass.data[DOMAIN][self.entry.entry_id][self.ip][
            "config_type"
        ]
        openwrt_devid = config_types.get(config_type, {}).get("openwrt-devid")

        # 1) Fetch live device state
        key_path = self.hass.data[DOMAIN]["config"]["ssh_key_path"]
        client = OpenWRTSSH(self.ip, key_path)

        (
            os_version,
            status,
            fw_downloaded,
            fw_file,
            hostname,
            distribution,
            target,
            board_name,
            pkgs,
        ) = await client.async_get_device_info()

        # 2) Resolve TOH for this device from the shared cache
        toh_coord = self.hass.data[DOMAIN].get("toh_cache")
        if not toh_coord:
            _LOGGER.debug("TOH cache is not read; keeping previous snapshot")
            return self.data or {}
        toh_item = toh_coord.get_for_devid(openwrt_devid)

        # 3) Produce a typed snapshot for entities
        result = {
            "current_os_version": os_version,
            "status": status,
            "available_os_version": getattr(toh_item, "version", None),
            "snapshot_url": getattr(toh_item, "snapshot_url", None),
            "compatibles": getattr(toh_item, "compatibles", None),
            "firmware_downloaded": fw_downloaded,
            "firmware_file": fw_file,
            "hostname": hostname,
            "distribution": distribution,
            "target": target,
            "board_name": board_name,
            "packages": pkgs,
        }
        _LOGGER.debug(
            "Coordinator data: %s",
            result,
        )
        return result
