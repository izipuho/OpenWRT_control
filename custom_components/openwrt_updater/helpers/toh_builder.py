"""TOH parser and indexer used by the TOH cache coordinator."""

from __future__ import annotations

import json
import logging
from typing import Any

from aiohttp import ClientTimeout

from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


class LocalTOH:
    """Building local TOH based on SysUpgrade overview and profiles JSONs.

    Responsibilities:.
    - Download raw SysUpgrade overview (network)..
    - Build an in-memory index for existing devices lookups by openwrt_devid..

    """

    def __init__(self, hass: HomeAssistant) -> None:
        """Initialize TOH wrapper."""
        self.hass = hass
        self.index: dict[str, Any] = {}

        self._base_url = hass.data[DOMAIN].get("config", {})["download_base_url"]
        self._headers = {
            "User-Agent": "OpenWRT-Control (Home Assistant)",
            "Accept": "application/json, text/plain, */*",
        }

    async def build_index(self, raw: dict[str, Any]) -> None:
        """Parse SysUpgrade Overview JSON. Build local index based on configured devices.

        Args:
            raw: Raw SysUpgrade overview JSON structure.

        """
        # try:
        orig_boards = self.hass.data[DOMAIN]["boards"]
        my_targets = {target: set(boards) for target, boards in orig_boards.items()}
        branches = raw.get("branches", {})
        # Ignore snapshot branch
        branches.pop("SNAPSHOT")
        # Iterate through branches
        for branch in branches.values():
            # Get last version from supported
            version = branch["versions"][0]
            # Iterate through my targets
            for target, boards in dict(my_targets).items():
                # Init index for target
                # _LOGGER.error("Adding target %s to index", target)
                self.index.setdefault(target, {})
                # Check if my target is in this branch
                if target in branch.get("targets", []):
                    # Get profiles for this target
                    profiles = await self._download_profile(version, target)
                    # Iterate through my boards within my target
                    for board in list(boards):
                        # Check if my board is in profiles
                        board_derived = board.replace(",", "_")
                        if board_derived in profiles:
                            # If IS then save it to index and remove it from scope
                            # _LOGGER.warning("Adding board %s to %s", board, target)
                            self.index[target].setdefault(
                                board, {"version": "", "sysupgrade_url": ""}
                            )
                            self.index[target][board]["version"] = version
                            self.index[target][board]["sysupgrade_url"] = profiles[
                                board_derived
                            ]
                            my_targets[target].remove(board)
                    # Remove whole target from scope if empty
                    if len(my_targets[target]) == 0:
                        my_targets.pop(target)
                if len(my_targets) == 0:
                    break
        # except Exception as e:
        #    _LOGGER.error("SysUpgrade overview parse failed: %s", e)

    async def _download_profile(self, version, target) -> list[list[str]]:
        """Download profile file for target and board.

        Args:
            version: version to check (e.g., "24.10.2")
            target: target to check (eg., "ramips/mt7621")

        Returns:
            dict with boards in this version for this target with sysupgrade URL

        """
        base_url = f"{self._base_url}releases/{version}/targets/{target}/"
        result = {}
        session = async_get_clientsession(self.hass)
        timeout = ClientTimeout(total=5)
        async with session.get(
            f"{base_url}profiles.json", headers=self._headers, timeout=timeout
        ) as resp:
            _LOGGER.debug("Download profiles for %s_%s", version, target)
            resp.raise_for_status()
            try:
                profiles_downloaded = await resp.json(content_type=None)
            except Exception as e:
                _LOGGER.debug("Response .json() failed: %s", e)
                text = await resp.text()
                profiles_downloaded = self._loads_json_text(text)

            profiles = profiles_downloaded["profiles"]
            for board in profiles:
                sysupgrade = next(
                    (
                        img
                        for img in profiles[board]["images"]
                        if img["type"] == "sysupgrade"
                    ),
                    None,
                )
                if sysupgrade:
                    result[board] = f"{base_url}{sysupgrade['name']}"

        return result

    async def download_overview(self) -> dict[str, Any]:
        """Download SysUpgrade overview JSON from the network with robust parsing and a local fallback.

        - Uses HA's shared aiohttp session.
        - Ignores incorrect Content-Type headers when parsing JSON.

        Returns:
            dict[str, Any]: Raw TOH structure.

        Raises:
            RuntimeError: If both network and local fallback fail or payload is invalid.

        """
        url = self.hass.data[DOMAIN]["config"]["overview_url"]
        session = async_get_clientsession(self.hass)
        timeout = ClientTimeout(total=5)
        # Try network first
        try:
            async with session.get(url, headers=self._headers, timeout=timeout) as resp:
                resp.raise_for_status()
                # Try JSON regardless of Content-Type
                try:
                    raw = await resp.json(content_type=None)
                    _LOGGER.warning(
                        "Got web data: %d rows, %s",
                        len(raw),
                        list(raw["branches"].keys())[:3],
                    )
                except Exception as json_err:
                    _LOGGER.error(
                        "Response .json() failed, falling back to text parse: %s",
                        json_err,
                    )
                    text = await resp.text()
                    raw = self._loads_json_text(text)

                if not isinstance(raw, dict):
                    raise TypeError("Unexpected TOH payload shape (not a JSON object)")
                return raw

        except Exception as net_err:
            _LOGGER.warning("Overview online fetch failed: %s", net_err)
            return {}

    @staticmethod
    def _loads_json_text(text: str):
        """Parse JSON from text robustly (handles BOM and stray whitespace).

        Args:
            text: Raw text that should contain JSON.

        Returns:
            Any: Parsed JSON value.

        """
        cleaned = (text or "").lstrip("\ufeff").strip()
        if not cleaned:
            # Nothing to parse – return empty dict so callers can handle gracefully
            raise ValueError("Empty response body while expecting JSON")
        # Quick heuristic to catch HTML error pages early
        if cleaned[:1] in ("<",) and "</html>" in cleaned.lower():
            raise ValueError("Received HTML instead of JSON (likely an error page)")
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
