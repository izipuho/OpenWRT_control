"""Typed helpers for coordinator payloads (dataclasses, no TypedDict)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class TohItem:
    """Normalized view of a single device entry from TOH cache."""

    version: str | None = None
    target: str | None = None
    subtarget: str | None = None
    snapshot_url: str | None = None


@dataclass(slots=True)
class DeviceData:
    """Data snapshot produced by the device coordinator for entities to consume."""

    current_os_version: str | None = None
    status: bool | None = None
    available_os_version: str | None = None
    snapshot_url: str | None = None
    firmware_downloaded: bool | None = None
    firmware_file: str | None = None
    hostname: str | None = None
