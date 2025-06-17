"""Constants and helpers."""

DOMAIN = "openwrt_updater"
CONFIG_TYPES_PATH = "custom_components/openwrt_updater/config_types.yaml"


def get_device_info(ip: str) -> dict:
    """Return device info for all platforms based on IP."""
    return {
        "identifiers": {(DOMAIN, ip)},
        "name": f"OpenWRT {ip}",
        "manufacturer": "OpenWRT",
        "model": "Router",
    }
