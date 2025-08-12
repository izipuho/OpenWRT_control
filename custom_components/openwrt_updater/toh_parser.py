"""Provide TOH parser."""

import json
import logging
from pathlib import Path

from aiohttp import ClientTimeout

from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


class TOH:
    """OpenWRT Table of Hardware."""

    def __init__(self, hass: HomeAssistant) -> None:
        """Initialize TOH class."""
        self.hass = hass
        self.session = async_get_clientsession(hass)
        self.url = hass.data.get(DOMAIN, {}).get("config", {}).get("TOH_url")
        self._toh_data = None
        self.version = ""
        self.target = ""
        self.subtarget = ""
        self.snapshot_url = ""

    async def fetch(self):
        """Fetch TOH data from openwrt.org using HA's HTTP session."""
        headers = {
            "User-Agent": "OpenWRT-Updater (HAss)",
        }
        try:
            timeout = ClientTimeout(total=5)
            async with self.session.get(
                self.url, headers=headers, timeout=timeout
            ) as resp:
                resp.raise_for_status()
                self._toh_data = await resp.json(content_type=None)
        except Exception as e:
            _LOGGER.warning(
                "TOH online fetch failed: %s. Falling back to bundled toh.json", e
            )
            try:
                local = Path(__file__).with_name("toh.json")
                self._toh_data = json.loads(local.read_text(encoding="utf-8"))
            except Exception as e2:
                _LOGGER.error("Local TOH fallback failed: %s", e2)
                self._toh_data = None

    def get_device_info(self, openwrt_devid: str) -> None:
        """Extract info for given openwrt device id from cached TOH data."""
        if not self._toh_data:
            return
        try:
            cols = self._toh_data["columns"]
            c = {
                name: cols.index(name)
                for name in (
                    "target",
                    "subtarget",
                    "supportedcurrentrel",
                    "firmwareopenwrtsnapshotupgradeurl",
                )
            }
            for dev in self._toh_data["entries"]:
                if dev[0] == openwrt_devid:
                    self.version = dev[c["supportedcurrentrel"]]
                    self.target = dev[c["target"]]
                    self.subtarget = dev[c["subtarget"]]
                    self.snapshot_url = dev[c["firmwareopenwrtsnapshotupgradeurl"]][0]
                    break
        except Exception as e:
            _LOGGER.error("Error parsing TOH data: %s", e)
