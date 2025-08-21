"""Initialize coordinators."""

from .device import OpenWRTDeviceCoordinator
from .toh import TohCacheCoordinator

__all__ = ["OpenWRTDeviceCoordinator", "TohCacheCoordinator"]
