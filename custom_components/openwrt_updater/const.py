"""Constants and helpers."""

DOMAIN = "openwrt_updater"
CONF_IP = "ip"
CONF_CONFIG_TYPE = "config_type"
CONFIG_FILE = "config_types.yaml"
KEY_PATH = "ssh_keys/id_ed25519"
CONFIG_TYPES_PATH = "custom_components/openwrt_updater/config_types.yaml"
TOH_URL = "https://openwrt.org/toh.json"


def get_device_info(ip: str) -> dict:
    """Return device info for all platforms based on IP."""
    return {
        "identifiers": {(DOMAIN, ip)},
        "name": f"OpenWRT {ip}",
        "manufacturer": "OpenWRT",
        "model": "Router",
    }
