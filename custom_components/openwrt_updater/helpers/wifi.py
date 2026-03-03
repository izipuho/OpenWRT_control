"""Wi-Fi policy helpers for OpenWRT."""

from __future__ import annotations

import hashlib

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .ssh_client import OpenWRTSSH


def resolve_wifi_policy(hass: HomeAssistant, entry: ConfigEntry, ip: str) -> dict:
    """Build effective policy in order: global -> place -> device."""
    global_config = hass.data[DOMAIN].get("config", {})
    place_name = str(entry.data.get("place_name", ""))

    mobility_domain = global_config.get("wifi_roaming_mobility_domain")
    if mobility_domain is None:
        mobility_domain = hashlib.sha1(place_name.encode("utf-8")).hexdigest()[:4]

    policy = {
        "roaming_enabled": global_config.get("wifi_roaming_enabled"),
        "mobility_domain": mobility_domain,
        "ft_over_ds": global_config.get("wifi_roaming_ft_over_ds"),
        "ft_psk_generate_local": global_config.get("wifi_roaming_ft_psk_generate_local"),
        "source": "global",
    }

    place_policy = entry.options.get("wifi_policy")
    if place_policy:
        policy.update(place_policy)
        policy["source"] = "place"

    device_policy = entry.options.get("devices", {}).get(ip, {}).get("wifi_policy")
    if device_policy:
        policy.update(device_policy)
        policy["source"] = "device"

    if policy.get("mobility_domain") is None:
        policy["mobility_domain"] = hashlib.sha1(place_name.encode("utf-8")).hexdigest()[:4]

    return policy


def _ap_wifi_ifaces(sections: list[dict]) -> list[dict]:
    """Return AP wifi-iface sections only."""
    return [
        section
        for section in sections
        if section.get("type") == "wifi-iface"
        and section.get("options", {}).get("mode") == "ap"
    ]


def _room_from_hostname(hostname: str | None) -> str | None:
    """Extract room from hostname with format {place}-{room}."""
    if not hostname or "-" not in hostname:
        return None
    room = hostname.split("-", 1)[1].strip()
    return room or None


def _role_from_ssid(ssid: str | None) -> str:
    """Map SSID to role name for interface mask."""
    if ssid and ssid.lower().endswith("-iot"):
        return "iot"
    return "main"


def _phy_from_device(device: str | None) -> str:
    """Map radio device name to phy suffix."""
    if device and "5" in device:
        return "ax"
    return "n"


def _build_ifname(room: str, role: str, phy: str) -> str:
    """Build interface name in agreed format."""
    return f"{room}-{role}-{phy}"


def _quote_uci(value: str) -> str:
    """Escape value for single-quoted UCI batch string."""
    return value.replace("'", "'\\''")


async def apply_wifi_policy(ip: str, key_path: str, policy: dict, hostname: str | None) -> bool:
    """Apply roaming policy with uci batch + commit + wifi reload."""
    async with OpenWRTSSH(ip=ip, key_path=key_path, command_timeout=40.0) as client:
        sections = await client.read_wireless_sections()
        ap_sections = _ap_wifi_ifaces(sections)

        if not ap_sections:
            return True

        roaming_enabled = bool(policy.get("roaming_enabled"))
        mobility_domain = policy.get("mobility_domain")
        ft_over_ds = bool(policy.get("ft_over_ds"))
        ft_psk_generate_local = bool(policy.get("ft_psk_generate_local"))
        room = _room_from_hostname(hostname)

        batch_lines: list[str] = []
        for section in ap_sections:
            name = section.get("name")
            if not name:
                continue

            options = section.get("options", {})
            batch_lines.append(
                f"set wireless.{name}.ieee80211r={'1' if roaming_enabled else '0'}"
            )

            if roaming_enabled:
                if mobility_domain is None:
                    return False
                batch_lines.append(
                    f"set wireless.{name}.mobility_domain='{_quote_uci(str(mobility_domain))}'"
                )
                batch_lines.append(
                    f"set wireless.{name}.ft_over_ds={'1' if ft_over_ds else '0'}"
                )
                batch_lines.append(
                    f"set wireless.{name}.ft_psk_generate_local={'1' if ft_psk_generate_local else '0'}"
                )

                if room:
                    role = _role_from_ssid(options.get("ssid"))
                    phy = _phy_from_device(options.get("device"))
                    ifname = _build_ifname(room, role, phy)
                    batch_lines.append(
                        f"set wireless.{name}.ifname='{_quote_uci(ifname)}'"
                    )
                    batch_lines.append(
                        f"set wireless.{name}.nasid='{_quote_uci(ifname)}'"
                    )
            else:
                batch_lines.append(f"delete wireless.{name}.mobility_domain")
                batch_lines.append(f"delete wireless.{name}.ft_over_ds")
                batch_lines.append(f"delete wireless.{name}.ft_psk_generate_local")

        if not batch_lines:
            return True

        batch_payload = "\n".join(batch_lines)
        command = f"""uci batch <<'END_UCI'
{batch_payload}
END_UCI
uci commit wireless
wifi reload
"""
        result = await client.exec_command(command=command, timeout=40.0)

    return bool(result is not None and result.exit_status == 0)
