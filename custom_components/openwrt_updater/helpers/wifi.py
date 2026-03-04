"""Wi-Fi policy helpers for OpenWRT."""

from __future__ import annotations

import hashlib
import logging
from typing import TYPE_CHECKING

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .ssh_client import OpenWRTSSH

if TYPE_CHECKING:
    from ..coordinators.device import OpenWRTDeviceCoordinator

_LOGGER = logging.getLogger(__name__)


def _derive_mobility_domain(place_name: str) -> str:
    """Derive deterministic 4-char mobility domain from place name."""
    return hashlib.sha1(place_name.encode("utf-8")).hexdigest()[:4]


def build_place_wifi_policy(place_name: str, policy_values: dict | None) -> dict:
    """Return place policy with normalized deterministic mobility domain."""
    policy = dict(policy_values or {})
    policy["mobility_domain"] = _derive_mobility_domain(place_name)
    return policy


def resolve_wifi_policy(_hass: HomeAssistant, entry: ConfigEntry, ip: str) -> dict:
    """Build effective policy in order: place -> device."""
    place_name = str(entry.data.get("place_name", ""))
    place_policy_saved = entry.options.get("wifi_policy")
    place_policy = build_place_wifi_policy(place_name, place_policy_saved)

    policy = dict(place_policy)
    policy["source"] = "place"

    device_policy = entry.options.get("devices", {}).get(ip, {}).get("wifi_policy")
    if device_policy:
        policy.update(device_policy)
        policy["source"] = "device"

    # Keep mobility domain tied to place policy, not device overrides.
    policy["mobility_domain"] = place_policy.get("mobility_domain")

    return policy



def _quote_uci(value: str) -> str:
    """Escape value for single-quoted UCI batch string."""
    return value.replace("'", "'\\''")


async def apply_wifi_policy(
    coordinator: OpenWRTDeviceCoordinator,
    policy: dict,
    debug_mode: bool = False,
) -> bool:
    """Apply policy or log planned UCI changes without applying in debug mode."""
    if not coordinator.last_update_success or not coordinator.data:
        return False

    status = coordinator.data.get("status")
    wifi_ifaces = coordinator.data.get("wifi_ifaces") or []
    wifi_radios = coordinator.data.get("wifi_radios") or []
    hostname = coordinator.data.get("hostname")

    if not status or not wifi_ifaces:
        return False

    radios_by_name = {
        str(radio.get("name")): radio for radio in wifi_radios if radio.get("name")
    }

    roaming_enabled = bool(policy.get("roaming_enabled"))
    mobility_domain = policy.get("mobility_domain")
    ft_over_ds = bool(policy.get("ft_over_ds"))
    ft_psk_generate_local = bool(policy.get("ft_psk_generate_local"))

    room = None
    if hostname and "-" in str(hostname):
        room = str(hostname).split("-", 1)[1].strip() or None

    batch_lines: list[str] = []
    for iface in wifi_ifaces:
        section = iface.get("name")
        if not section:
            continue

        section_name = str(section)
        batch_lines.append(
            f"set wireless.{section_name}.ieee80211r={'1' if roaming_enabled else '0'}"
        )

        if roaming_enabled:
            if mobility_domain is None:
                return False
            batch_lines.append(
                f"set wireless.{section_name}.mobility_domain='{_quote_uci(str(mobility_domain))}'"
            )
            batch_lines.append(
                f"set wireless.{section_name}.ft_over_ds={'1' if ft_over_ds else '0'}"
            )
            batch_lines.append(
                f"set wireless.{section_name}.ft_psk_generate_local={'1' if ft_psk_generate_local else '0'}"
            )

            if room:
                role = str(iface.get("role") or "").strip().lower()
                if role not in {"main", "iot"}:
                    role = (
                        "iot"
                        if str(iface.get("ssid", "")).lower().endswith("-iot")
                        else "main"
                    )

                band = str(iface.get("band") or "").strip().lower()
                if not band:
                    radio = radios_by_name.get(str(iface.get("device")))
                    band = str((radio or {}).get("band") or "").strip().lower()
                if not band:
                    band = "2g"

                ifname = f"{room}-{role}-{band}"
                batch_lines.append(
                    f"set wireless.{section_name}.ifname='{_quote_uci(ifname)}'"
                )
                batch_lines.append(
                    f"set wireless.{section_name}.nasid='{_quote_uci(ifname)}'"
                )
        else:
            batch_lines.append(f"delete wireless.{section_name}.mobility_domain")
            batch_lines.append(f"delete wireless.{section_name}.ft_over_ds")
            batch_lines.append(f"delete wireless.{section_name}.ft_psk_generate_local")

    if not batch_lines:
        return False

    batch_payload = "\n".join(batch_lines)
    command = f"""uci batch <<'END_UCI'
{batch_payload}
END_UCI
uci commit wireless
wifi reload
"""

    if debug_mode:
        _LOGGER.warning(
            "Wi-Fi policy debug_mode enabled for %s: no changes applied",
            coordinator.ip,
        )
        _LOGGER.warning("UCI batch payload for %s:\n%s", coordinator.ip, batch_payload)
        _LOGGER.warning("UCI command preview for %s:\n%s", coordinator.ip, command)
        return True

    key_path = coordinator.hass.data[DOMAIN]["config"]["ssh_key_path"]
    async with OpenWRTSSH(
        ip=coordinator.ip,
        key_path=key_path,
        command_timeout=40.0,
    ) as client:
        result = await client.exec_command(command=command, timeout=40.0)

    return bool(result is not None and result.exit_status == 0)
