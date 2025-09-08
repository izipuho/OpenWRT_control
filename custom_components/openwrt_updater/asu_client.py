"""Minimal async client for the Attended Sysupgrade (ASU) server."""

from __future__ import annotations

import logging

import asyncio

import aiohttp

_LOGGER = logging.getLogger(__name__)


class ASUClient:
    """Minimal async client for the Attended Sysupgrade (ASU) server."""

    def __init__(self, base_url: str, token: str | None = None) -> None:
        """Initialize client with base URL and optional bearer token."""
        self.base_url = base_url.removesuffix("/")
        self.token = token
        self.headers = {"Accept": "application/json"}
        if self.token:
            self.headers["Authorization"] = f"Bearer {self.token}"

    async def _post_json(self, path: str, payload: dict, timeout: float = 60.0) -> dict:
        """Send POST with JSON payload and return parsed JSON response."""
        url = f"{self.base_url}{path}"
        async with (
            aiohttp.ClientSession() as sess,
            sess.post(url, json=payload, headers=self.headers, timeout=timeout) as resp,
        ):
            if resp.status // 100 != 2:
                text = await resp.text()
                raise RuntimeError(f"ASU POST {path} failed ({resp.status}): {text}")
            return await resp.json(content_type=None)

    async def _get_json(self, path: str, timeout: float = 60.0) -> dict:
        """Send GET request and return parsed JSON response."""
        url = f"{self.base_url}{path}"
        async with (
            aiohttp.ClientSession() as sess,
            sess.get(url, headers=self.headers, timeout=timeout) as resp,
        ):
            if resp.status // 100 != 2:
                text = await resp.text()
                raise RuntimeError(f"ASU GET failed ({resp.status}): {text}")
            return await resp.json(content_type=None)

    async def build_request(
        self,
        version: str,
        target: str,
        board_name: str,
        packages: list[str],
        client_name: str,
        distribution: str = "openwrt",
        timeout: float = 60.0,
    ) -> dict:
        """Create an upgrade request and return JSON response.

        Args:
            version: Version to install, e.g. "23.05.5".
            target: Installed target, e.g. "mvebu/cortexa9".
            board_name: Board name from 'ubus call system board', e.g. "ubnt,unifi-6-lite".
            packages: List of installed package names.
            client_name: Client name and version that requests the image.
            distribution: Installed distribution, e.g. "OpenWrt".
            timeout: HTTP request timeout.

        Returns:
            JSON dict with request_hash or status link.

        """
        payload: dict = {
            "distro": distribution,
            "version": version,
            "target": target,
            "profile": board_name,
            "packages": packages,
            "diff_packages": "true",
            "client": client_name,
        }
        return await self._post_json("/api/v1/build", payload, timeout=timeout)

    async def poll_build_request(
        self,
        request_hash: str,
        *,
        interval: float = 2.0,
        timeout: float = 900.0,
    ) -> dict:
        """Poll upgrade-request status until ready or error.

        Args:
            request_hash: Hash returned from upgrade_request().
            interval: Delay between polls in seconds.
            timeout: Maximum time to wait in seconds.

        Returns:
            bin_dir: web directory storing current build
            file_name: firmware file name

        Raises:
            RuntimeError if timeout expires before result is ready.

        """
        status_url = f"{self.base_url}/api/v1/build/{request_hash}"
        _LOGGER.error("Request url: %s", status_url)
        deadline = asyncio.get_running_loop().time() + timeout
        last_payload: dict | None = None

        while True:
            last_payload = await self._get_json(status_url, timeout=60.0)
            state = str(last_payload.get("detail") or "").lower()
            if state == "done":
                bin_dir = last_payload.get("bin_dir")
                file_name = last_payload.get("images")[0].get("name")
                return bin_dir, file_name

            if asyncio.get_running_loop().time() > deadline:
                raise RuntimeError(
                    f"ASU poll timeout for {request_hash}; last state: {state or 'unknown'}"
                )

            await asyncio.sleep(interval)
