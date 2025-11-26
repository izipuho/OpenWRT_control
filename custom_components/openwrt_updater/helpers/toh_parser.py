"""TOH parser and indexer used by the TOH cache coordinator."""

from __future__ import annotations

from functools import partial
import json
import logging
from pathlib import Path
from typing import Any

from aiohttp import ClientTimeout

from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import DOMAIN
from .types import TohItem

_LOGGER = logging.getLogger(__name__)


class TOH:
    """Wrapper around OpenWRT Table of Hardware (TOH).

    Responsibilities:
    - Download raw TOH (network) via your existing logic.
    - Load persisted raw TOH (offline).
    - Build an in-memory index for O(1) lookups by openwrt_devid.
    """

    def __init__(self, hass: HomeAssistant) -> None:
        """Initialize TOH wrapper."""
        self.hass = hass
        self.data: dict[str, Any] = {}
        self._index: dict[str, TohItem] = {}

    async def fetch(self) -> dict[str, Any]:
        """Download raw TOH and rebuild the in-memory index.

        Returns:
            dict[str, Any]: Raw TOH structure as downloaded.

        """
        raw = await self.download_toh()
        self.load(raw)
        return self.data

    def load(self, raw: dict[str, Any]) -> None:
        """Load raw TOH without network and rebuild the in-memory index.

        Args:
            raw: Raw TOH JSON structure (same shape as produced by fetch()).

        """
        self.data = raw or {}
        self._index = {}
        if not self.data:
            _LOGGER.warning("TOH: empty raw data")
            return

        try:
            cols = self.data.get("columns", []) or []
            entries = self.data.get("entries", []) or []

            # Resolve column indices with safe fallbacks.
            id_idx = self._col(cols, ["id", "devid", "deviceid"])
            ver_idx = self._col(cols, ["supportedcurrentrel", "version"])
            tgt_idx = self._col(cols, ["target"])
            sub_idx = self._col(cols, ["subtarget"])
            snap_idx = self._col(
                cols, ["firmwareopenwrtsnapshotupgradeurl", "snapshot_url"]
            )

            _LOGGER.debug(
                "TOH: building index | rows=%d id_idx=%s ver_idx=%s tgt_idx=%s sub_idx=%s snap_idx=%s",
                len(entries),
                id_idx,
                ver_idx,
                tgt_idx,
                sub_idx,
                snap_idx,
            )

            # Build the index directly here (no extra helper method).
            for row in entries:
                if not isinstance(row, list) or len(row) == 0:
                    continue

                devid = self._safe_cell(row, id_idx)
                if not isinstance(devid, str) or not devid:
                    continue

                # First occurrence wins to avoid accidental overrides.
                if devid in self._index:
                    continue

                version = self._safe_cell(row, ver_idx)
                target = self._safe_cell(row, tgt_idx)
                subtarget = self._safe_cell(row, sub_idx)
                snapshot_url = self._normalize_snapshot_url(
                    self._safe_cell(row, snap_idx)
                )

                self._index[devid] = TohItem(
                    version=str(version) if version is not None else None,
                    target=str(target) if target is not None else None,
                    subtarget=str(subtarget) if subtarget is not None else None,
                    snapshot_url=snapshot_url,
                )
        except Exception as exc:  # noqa: BLE001
            _LOGGER.error("TOH index build error: %s", exc)

    def get_device_info(self, devid: str) -> TohItem:
        """Get normalized TOH info for a device id (offline only).

        Args:
            devid: Device identifier used in TOH (e.g., 'tplink_archer-c7-v2').

        Returns:
            TohItem: Normalized TOH info; empty TohItem if not found.

        """
        return self._index.get(devid, TohItem())

    async def download_toh(self) -> dict[str, Any]:
        """Download TOH JSON from the network with robust parsing and a local fallback.

        - Uses HA's shared aiohttp session.
        - Ignores incorrect Content-Type headers when parsing JSON.
        - Falls back to bundled 'toh.json' on network/parsing errors.

        Returns:
            dict[str, Any]: Raw TOH structure.

        Raises:
            RuntimeError: If both network and local fallback fail or payload is invalid.

        """
        url = self.hass.data[DOMAIN]["config"]["toh_url"]
        session = async_get_clientsession(self.hass)
        headers = {
            "User-Agent": "OpenWRT-Control (Home Assistant)",
            "Accept": "application/json, text/plain, */*",
        }
        timeout = ClientTimeout(total=5)

        # Try network first
        try:
            async with session.get(url, headers=headers, timeout=timeout) as resp:
                resp.raise_for_status()
                # Try JSON regardless of Content-Type
                try:
                    raw = await resp.json(content_type=None)
                    _LOGGER.debug("Got web data: %d rows", len(raw))
                except Exception as json_err:  # noqa: BLE001
                    _LOGGER.debug(
                        "Response .json() failed, falling back to text parse: %s",
                        json_err,
                    )
                    text = await resp.text()
                    raw = self._loads_json_text(text)

                if not isinstance(raw, dict):
                    raise TypeError("Unexpected TOH payload shape (not a JSON object).")
                return raw

        except Exception as net_err:  # noqa: BLE001
            _LOGGER.warning(
                "TOH online fetch failed: %s. Falling back to bundled toh.json", net_err
            )

        # Fallback to packaged file (read off the event loop)
        try:
            local_path = Path(__file__).with_name("toh.json")
            read_text = partial(local_path.read_text, encoding="utf-8")
            text = await self.hass.async_add_executor_job(read_text)
            raw = self._loads_json_text(text)
            if not isinstance(raw, dict):
                raise TypeError(
                    "Bundled TOH fallback has unexpected shape (not a JSON object)."
                )
        except Exception as fs_err:
            _LOGGER.error("Local TOH fallback failed: %s", fs_err)
            raise RuntimeError(
                "Failed to obtain TOH from network and local fallback."
            ) from fs_err
        else:
            return raw

    @staticmethod
    def _loads_json_text(text: str):
        """Parse JSON from text robustly (handles BOM and stray whitespace).

        Args:
            text: Raw text that should contain JSON.

        Returns:
            Any: Parsed JSON value.

        """
        # Strip BOM and whitespace to be tolerant of mirror quirks
        cleaned = text.lstrip("\ufeff").strip()
        return json.loads(cleaned)

    @staticmethod
    def _col(
        columns_map: list[str],
        candidates: list[str],
    ) -> int | None:
        """Resolve a column index by trying several candidate names.

        Args:
            columns_map: Mapping of column name to index from TOH payload.
            candidates: Ordered list of possible names for the column.

        Returns:
            int | None: Column index if found, otherwise default.

        """
        try:
            for name in candidates:
                if name in columns_map:
                    return columns_map.index(name)
        except Exception as e:
            _LOGGER.error("Index get failed: %s", e)
            return -1

    @staticmethod
    def _safe_cell(row: list[Any], idx: int | None) -> Any:
        """Safely return a cell value by index.

        Args:
            row: Row array from TOH 'entries'.
            idx: Column index or None.

        Returns:
            Any: Cell value or None if unavailable.

        """
        if idx is None:
            return None
        if idx < 0 or idx >= len(row):
            return None
        return row[idx]

    @staticmethod
    def _normalize_snapshot_url(value: Any) -> str | None:
        """Normalize snapshot URL cell into a string.

        Args:
            value: Cell value which can be a string, list[str], or None.

        Returns:
            str | None: URL string if present, otherwise None.

        """
        if value is None:
            return None
        if isinstance(value, list):
            return value[0] if value else None
        if isinstance(value, str):
            return value or None
        return None
