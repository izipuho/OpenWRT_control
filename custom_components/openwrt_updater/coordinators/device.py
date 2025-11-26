"""Device coordinator that merges SSH state with cached TOH info."""

from __future__ import annotations

from datetime import timedelta
import logging
from typing import TYPE_CHECKING, Any

from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from ..helpers.const import DOMAIN, SIGNAL_BOARDS_CHANGED

# from ..helpers.helpers import load_config_types
from ..helpers.ssh_client import OpenWRTSSH

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

        self._toh = hass.data[DOMAIN]["toh_index"]
        self._unsub_toh = self._toh.async_add_listener(self._on_toh_update)
        self._pair_registered = False

    def _on_toh_update(self) -> None:
        """TOH changed -> update my entities WITHOUT SSH."""
        self.hass.async_create_task(self.async_request_refresh())

    async def _async_update_data(self):
        """Fetch device state and compose a DeviceData snapshot.

        - Live device state is fetched via `get_dev_state()`.
        - TOH info is resolved from the shared TohCacheCoordinator (no network).
        """
        _LOGGER.debug("Update coordinator for %s", self.ip)
        config_types_path = self.hass.data[DOMAIN]["config"]["config_types_path"]
        # config_types = await self.hass.async_add_executor_job(load_config_types, config_types_path)
        # config_type = self.hass.data[DOMAIN][self.entry.entry_id][self.ip]["config_type"]

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
            has_asu_client,
        ) = await client.async_get_device_info()

        # 1.1) Gather boards
        if target and board_name and not self._pair_registered:
            boards_registry = self.hass.data[DOMAIN]["boards"]
            if board_name not in boards_registry.setdefault(target, set()):
                boards_registry[target].add(board_name)
                async_dispatcher_send(self.hass, SIGNAL_BOARDS_CHANGED)
            self._pair_registered = True

        # 2) Resolve TOH for this device from the shared cache
        version, sysupgrade_url = self._toh.get_os_info(target, board_name)

        # 3) Produce a typed snapshot for entities
        result = {
            "current_os_version": os_version,
            "status": status,
            "available_os_version": version,
            "snapshot_url": sysupgrade_url,
            "firmware_downloaded": fw_downloaded,
            "firmware_file": fw_file,
            "hostname": hostname,
            "distribution": distribution,
            "target": target,
            "board_name": board_name,
            "has_asu_client": has_asu_client,
            "packages": pkgs,
        }
        _LOGGER.debug(
            "Coordinator data: %s",
            result,
        )
        return result
