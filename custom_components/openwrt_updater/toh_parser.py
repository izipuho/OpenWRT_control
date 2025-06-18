"""Provide TOH parser."""

import logging

import httpx

from homeassistant.core import HomeAssistant

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


class TOH:
    """OpenWRT Table of Hardware."""

    def __init__(self, hass: HomeAssistant) -> None:
        """Initialize TOH class."""
        self.hass = hass
        self._toh_data = None
        self.version = ""
        self.target = ""
        self.subtarget = ""
        self.snapshot_url = ""

    async def fetch(self):
        """Fetch TOH data from openwrt.org using HA's HTTP session."""
        toh_url = self.hass.data.get(DOMAIN, {}).get("config", {}).get("TOH_url", "")
        headers = {
            "User-Agent": "curl/8.12.1",
            "Accept": "*/*",
        }
        async with httpx.AsyncClient(http2=True, timeout=5.0) as client:
            try:
                response = await client.get(toh_url)
                response.raise_for_status()
            except httpx.HTTPError as err:
                _LOGGER.error("TOH HTTPx: %s", err)
                self._toh_data = None
            except Exception as e:
                _LOGGER.error("Failed to fetch TOH data: %s", e)
                self._toh_data = None
            else:
                self._toh_data = response.json()

    def get_device_info(self, openwrt_devid: str) -> None:
        """Extract info for given openwrt device id from cached TOH data."""
        if not self._toh_data:
            return
        try:
            target_col = self._toh_data["columns"].index("target")
            subtarget_col = self._toh_data["columns"].index("subtarget")
            version_col = self._toh_data["columns"].index("supportedcurrentrel")
            snapshot_url_col = self._toh_data["columns"].index(
                "firmwareopenwrtsnapshotupgradeurl"
            )

            for dev in self._toh_data["entries"]:
                if dev[0] == openwrt_devid:
                    self.version = dev[version_col]
                    self.target = dev[target_col]
                    self.subtarget = dev[subtarget_col]
                    self.snapshot_url = dev[snapshot_url_col][0]
                    break
        except Exception as e:
            _LOGGER.error("Error parsing TOH data: %s", e)
