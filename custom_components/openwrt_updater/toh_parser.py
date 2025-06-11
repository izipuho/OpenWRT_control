"""Provide TOH parser."""

import logging

import requests

from homeassistant.core import HomeAssistant

from .const import TOH_URL

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
        """Fetch and cache TOH data asynchronously."""

        def blocking_fetch():
            response = requests.get(TOH_URL, timeout=10)
            response.raise_for_status()
            return response.json()

        try:
            self._toh_data = await self.hass.async_add_executor_job(blocking_fetch)
        except Exception as e:
            _LOGGER.error("Failed to fetch TOH data: %s", e)
            self._toh_data = None
            return None
        else:
            return self._toh_data

    def get_device_info(self, openwrt_devid: str) -> None:
        """Extract available OS version for given openwrt device id from cached TOH data."""
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
