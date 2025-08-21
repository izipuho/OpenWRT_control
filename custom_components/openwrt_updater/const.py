"""Constants and helpers."""

DOMAIN = "openwrt_updater"

INTEGRATION_DEFAULTS = {
    "master_node": "zip@10.8.25.20",
    "builder_location": "/home/zip/OpenWrt-bulder/",
    "ssh_key_path": "ssh_keys/id_ed25519",
    "toh_url": "https://openwrt.org/toh.json",
    "config_types_file": "config_types.yaml",
    "toh_timeout_hours": 24,
    "device_timeout_minutes": 10,
}


def get_device_info(place_name: str, ip: str) -> dict:
    """Return device info for all platforms based on IP."""
    return {
        "identifiers": {(DOMAIN, ip)},
        "name": f"{place_name} {ip}",
        "manufacturer": "OpenWRT",
        "model": "Router",
    }
