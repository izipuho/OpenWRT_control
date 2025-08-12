"""Constants and helpers."""

DOMAIN = "openwrt_updater"


def get_device_info(place_name: str, ip: str) -> dict:
    """Return device info for all platforms based on IP."""
    return {
        "identifiers": {(DOMAIN, ip)},
        "name": f"{place_name} {ip}",
        "manufacturer": "OpenWRT",
        "model": "Router",
    }
