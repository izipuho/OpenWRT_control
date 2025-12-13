"""Initialize coordinators."""

from .device import OpenWRTDeviceCoordinator
from .sysupgrade import LocalTohCacheCoordinator

__all__ = [
    "LocalTohCacheCoordinator",
    "OpenWRTDeviceCoordinator",
]
