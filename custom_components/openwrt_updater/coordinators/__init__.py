"""Initialize coordinators."""

from .device import OpenWRTDeviceCoordinator
from .sysupgrade import LocalTohCacheCoordinator
from .toh import TohCacheCoordinator

__all__ = [
    "LocalTohCacheCoordinator",
    "OpenWRTDeviceCoordinator",
    "TohCacheCoordinator",
]
