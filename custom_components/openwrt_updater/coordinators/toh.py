"""Coordinator that refreshes and persists Table of Hardware (TOH) cache."""

from __future__ import annotations

import contextlib
import logging
from typing import TYPE_CHECKING, Any

from homeassistant.helpers.storage import Store
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from ..const import DOMAIN
from ..toh_parser import TOH
from ..types import TohItem

if TYPE_CHECKING:
    from datetime import timedelta

    from homeassistant.core import HomeAssistant


_LOGGER = logging.getLogger(__name__)

_STORE_VERSION = 1
_STORE_KEY = f"{DOMAIN}_toh_raw"


class TohCacheCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Maintains a persisted TOH cache and exposes a simple lookup.

    - Periodically fetches TOH from the network and saves raw JSON to HA Store.
    - On startup loads raw JSON from HA Store (so entities work offline).
    - Provides `get_for_devid()` to resolve a device id into a normalized TohItem.
    """

    def __init__(self, hass: HomeAssistant, update_interval: timedelta) -> None:
        """Initialize the coordinator with a given refresh interval."""
        super().__init__(
            hass=hass,
            logger=_LOGGER,
            name=f"{DOMAIN}-toh-cache",
            update_interval=update_interval,
        )
        self._store = Store(hass, _STORE_VERSION, _STORE_KEY)
        self._toh = TOH(hass)

    async def async_config_entry_first_refresh(self) -> None:
        """Preload cached TOH before the very first refresh so lookups work offline.

        This loads raw TOH from the Store into the TOH instance, then performs
        the regular first refresh lifecycle to try a network update.
        """
        cached = await self._store.async_load()
        if cached:
            try:
                self._toh.load(cached)
                _LOGGER.debug("TOH first refresh")
            except Exception:
                _LOGGER.warning("Failed to preload TOH cache", exc_info=True)
        await super().async_config_entry_first_refresh()

    async def _async_update_data(self) -> dict[str, Any]:
        """Refresh TOH from network and persist it; fallback to cached raw data.

        Returns the raw TOH dict (as downloaded). Entities should not parse
        this directly — use `get_for_devid()` for a normalized view.
        """
        cached = await self._store.async_load() or {}
        try:
            raw = await self._toh.fetch()
            await self._store.async_save(raw)
            _LOGGER.debug("Updating TOH cache: %d rows", len(raw))
        except Exception:
            _LOGGER.warning(
                "TOH update failed, using cached data if available", exc_info=True
            )
            if cached:
                with contextlib.suppress(Exception):
                    self._toh.load(cached)
                return cached
            raise
        else:
            return raw

    def get_for_devid(self, devid: str | None) -> TohItem:
        """Return normalized TOH info for a given device id.

        This never touches the network; it reads the in-memory TOH index.
        """
        if not devid:
            return TohItem()
        return self._toh.get_device_info(devid)
