"""Coordinator that refreshes and persists Table of Hardware (TOH) cache."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from homeassistant.core import callback
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.helpers.dispatcher import async_dispatcher_connect

from ..helpers.const import DOMAIN, SIGNAL_BOARDS_CHANGED
from ..helpers.toh_builder import LocalTOH
from ..helpers.types import TohItem

if TYPE_CHECKING:
    from datetime import timedelta

    from homeassistant.core import HomeAssistant


_LOGGER = logging.getLogger(__name__)


class LocalTohCacheCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Maintains a persisted TOH cache and exposes a simple lookup.

    - Periodically fetches TOH from the network and saves raw JSON to HA Store.
    - On startup loads raw JSON from HA Store (so entities work offline).
    """

    def __init__(self, hass: HomeAssistant, update_interval: timedelta) -> None:
        """Initialize the coordinator with a given refresh interval."""
        super().__init__(
            hass=hass,
            logger=_LOGGER,
            name=f"{DOMAIN}_sysupgrade_info",
            update_interval=update_interval,
        )
        self._toh = LocalTOH(hass)

        self._unsub_signal = async_dispatcher_connect(
            hass, SIGNAL_BOARDS_CHANGED, self._on_boards_changed
        )

    @callback
    async def _on_boards_changed(self) -> None:
        """React to new (target, board) pairs by requesting a refresh."""
        await self.async_request_refresh()

    async def async_will_remove_from_hass(self) -> None:
        """Unsubsribe from signals."""
        await super().async_will_remove_from_hass()
        if getattr(self, "_unsub_signal", None):
            self._unsub_signal()
            self._unsub_signal = None

    async def async_config_entry_first_refresh(self) -> None:
        """Preload cached TOH before the very first refresh so lookups work offline.

        This loads raw TOH from the Store into the TOH instance, then performs
        the regular first refresh lifecycle to try a network update.
        """
        await super().async_config_entry_first_refresh()

    async def _async_update_data(self) -> dict[str, Any]:
        """Refresh TOH from network; fallback to cached raw data.

        Returns builded index. Entities should not parse
        this directly — use `get_for_devid()` for a normalized view.
        """
        try:
            raw = await self._toh.download_overview()
            await self._toh.build_index(raw)
            result = self._toh.index
        except Exception:
            _LOGGER.warning(
                "TOH update failed, using cached data if available", exc_info=True
            )
        else:
            return result

    def get_os_info(self, target, board):
        """Parse index and return OS info for selected board."""
        os_info = (
            self.hass.data[DOMAIN]["toh_index"].data.get(target, {}).get(board, {})
        )
        if os_info == {}:
            return None, None
        return os_info["version"], os_info["sysupgrade_url"]
