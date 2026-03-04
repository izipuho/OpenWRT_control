"""OpenWRT place-level sensor entities."""

from datetime import datetime
from typing import Any

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect

from .helpers.const import DOMAIN, SIGNAL_PLACE_WIFI_POLICY_APPLY_CHANGED, get_place_device_info
from .helpers.wifi import resolve_wifi_policy


def _to_bool(value: Any) -> bool:
    """Normalize bool-ish values from UCI/JSON."""
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value != 0
    if value is None:
        return False
    return str(value).strip().lower() in {"1", "true", "yes", "on", "enabled"}


def _is_set(value: Any) -> bool:
    """Return whether value should be treated as configured."""
    return value not in (None, "")


class OpenWRTPlaceSensor(SensorEntity):
    """Represent a place-level sensor entity."""

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: ConfigEntry,
        name: str,
        key: str,
        device_class: SensorDeviceClass | None = None,
        entity_category: EntityCategory | None = None,
        icon: str | None = None,
    ) -> None:
        """Initialize the place sensor entity."""
        self.hass = hass
        self._config_entry = config_entry
        self._key = key
        self._place_name = str(config_entry.data.get("place_name", ""))
        self._signal = (
            f"{SIGNAL_PLACE_WIFI_POLICY_APPLY_CHANGED}_{self._config_entry.entry_id}"
        )

        self._attr_device_info = get_place_device_info(self._place_name)
        self._attr_name = f"{name} ({self._place_name})"
        self._attr_unique_id = f"{key}_{self._place_name.lower().replace(' ', '_')}"
        self._attr_device_class = device_class
        self._attr_entity_category = entity_category
        self._attr_icon = icon

    @property
    def should_poll(self) -> bool:
        """Disable polling, use dispatcher updates."""
        return False

    def _get_apply_data(self) -> dict[str, Any]:
        """Return cached place apply data."""
        entry_data = self.hass.data.get(DOMAIN, {}).get(self._config_entry.entry_id, {})
        return (
            entry_data.get("place_actions", {}).get("wifi_policy_apply", {})
            if entry_data
            else {}
        )

    def _evaluate_device_policy(self, ip: str, coordinator) -> dict[str, Any]:
        """Evaluate policy sync and non-standard markers for a single device."""
        if coordinator is None or not coordinator.last_update_success:
            return {"status": "unknown", "nonstandard": False, "reasons": []}

        data = coordinator.data or {}
        if not data.get("status"):
            return {"status": "unknown", "nonstandard": False, "reasons": []}

        wifi_ifaces = data.get("wifi_ifaces") or []
        wifi_radios = data.get("wifi_radios") or []
        if not wifi_ifaces:
            return {"status": "unknown", "nonstandard": False, "reasons": []}

        radios_by_name = {
            str(radio.get("name")): radio for radio in wifi_radios if radio.get("name")
        }
        hostname = data.get("hostname")
        room = None
        if hostname and "-" in str(hostname):
            room = str(hostname).split("-", 1)[1].strip() or None

        policy = resolve_wifi_policy(self.hass, self._config_entry, ip)
        roaming_enabled = bool(policy.get("roaming_enabled"))
        mobility_domain = policy.get("mobility_domain")
        ft_over_ds = bool(policy.get("ft_over_ds"))
        ft_psk_generate_local = bool(policy.get("ft_psk_generate_local"))

        drift = False
        nonstandard_reasons: list[str] = []

        for iface in wifi_ifaces:
            section = iface.get("name")
            if not section:
                continue
            section_name = str(section)

            role_raw = str(iface.get("role") or "").strip().lower()
            role = role_raw
            if role not in {"main", "iot"}:
                role = "iot" if str(iface.get("ssid", "")).lower().endswith("-iot") else "main"
                nonstandard_reasons.append(f"{ip}:{section_name}:unknown_role")
            is_main = role == "main"

            expected_ieee = roaming_enabled and is_main
            if _to_bool(iface.get("ieee80211r")) != expected_ieee:
                drift = True

            if roaming_enabled and is_main:
                if mobility_domain is None:
                    drift = True
                elif str(iface.get("mobility_domain") or "") != str(mobility_domain):
                    drift = True
                if _to_bool(iface.get("ft_over_ds")) != ft_over_ds:
                    drift = True
                if _to_bool(iface.get("ft_psk_generate_local")) != ft_psk_generate_local:
                    drift = True
            else:
                if _is_set(iface.get("mobility_domain")):
                    drift = True
                if _is_set(iface.get("ft_over_ds")):
                    drift = True
                if _is_set(iface.get("ft_psk_generate_local")):
                    drift = True

            if roaming_enabled and room:
                band = str(iface.get("band") or "").strip().lower()
                if not band:
                    radio = radios_by_name.get(str(iface.get("device")))
                    band = str((radio or {}).get("band") or "").strip().lower()
                if not band:
                    band = "2g"
                    nonstandard_reasons.append(f"{ip}:{section_name}:missing_band")

                expected_ifname = f"{room}-{role}-{band}"
                if str(iface.get("ifname") or "") != expected_ifname:
                    drift = True
                    nonstandard_reasons.append(f"{ip}:{section_name}:ifname_mismatch")

                if is_main:
                    if str(iface.get("nasid") or "") != expected_ifname:
                        drift = True
                        nonstandard_reasons.append(f"{ip}:{section_name}:nasid_mismatch")
            elif roaming_enabled and not room:
                nonstandard_reasons.append(f"{ip}:{section_name}:missing_room")

        return {
            "status": "drift" if drift else "in_sync",
            "nonstandard": bool(nonstandard_reasons),
            "reasons": nonstandard_reasons,
            "roaming_enabled": bool(data.get("wifi_roaming_enabled")),
        }

    def _build_place_stats(self) -> dict[str, Any]:
        """Build aggregate place-level stats."""
        entry_data = self.hass.data.get(DOMAIN, {}).get(self._config_entry.entry_id, {})
        devices = self._config_entry.options.get("devices", {})

        stats = {
            "devices_total": len(devices),
            "roaming_enabled_count": 0,
            "policy_in_sync_count": 0,
            "policy_drift_count": 0,
            "policy_unknown_count": 0,
            "nonstandard_count": 0,
            "nonstandard_ips": [],
            "nonstandard_reasons": {},
        }

        for ip in devices:
            coordinator = entry_data.get(ip, {}).get("coordinator")
            result = self._evaluate_device_policy(ip, coordinator)

            if result.get("roaming_enabled"):
                stats["roaming_enabled_count"] += 1

            status = result.get("status")
            if status == "in_sync":
                stats["policy_in_sync_count"] += 1
            elif status == "drift":
                stats["policy_drift_count"] += 1
            else:
                stats["policy_unknown_count"] += 1

            if result.get("nonstandard"):
                stats["nonstandard_count"] += 1
                stats["nonstandard_ips"].append(ip)
                stats["nonstandard_reasons"][ip] = result.get("reasons", [])

        return stats

    @property
    def native_value(self):
        """Return sensor value."""
        data = self._get_apply_data()
        stats = self._build_place_stats()

        if self._key == "wifi_policy_last_run_at":
            ts = data.get("last_run_at")
            return ts if isinstance(ts, datetime) else None
        if self._key == "devices_total":
            return stats["devices_total"]
        if self._key == "roaming_enabled_count":
            return stats["roaming_enabled_count"]
        if self._key == "policy_in_sync_count":
            return stats["policy_in_sync_count"]
        if self._key == "policy_drift_count":
            return stats["policy_drift_count"]
        if self._key == "policy_unknown_count":
            return stats["policy_unknown_count"]
        if self._key == "nonstandard_count":
            return stats["nonstandard_count"]
        if self._key == "nonstandard_devices":
            ips = stats["nonstandard_ips"]
            return ",".join(ips) if ips else ""
        if self._key == "wifi_policy_last_result":
            return str(data.get("result", "never_run"))
        if self._key == "wifi_policy_last_success_count":
            return int(data.get("success_count", 0))
        if self._key == "wifi_policy_last_fail_count":
            return int(data.get("fail_count", 0))
        if self._key == "wifi_policy_last_error_ips":
            ips = data.get("error_ips", [])
            return ",".join(ips) if ips else ""
        return None

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return optional sensor attributes."""
        if self._key == "wifi_policy_last_error_ips":
            data = self._get_apply_data()
            ips = data.get("error_ips", [])
            return {"ips": ips if isinstance(ips, list) else []}
        if self._key == "nonstandard_devices":
            stats = self._build_place_stats()
            return {
                "ips": stats["nonstandard_ips"],
                "reasons": stats["nonstandard_reasons"],
            }
        if self._key in {"policy_in_sync_count", "policy_drift_count", "policy_unknown_count"}:
            stats = self._build_place_stats()
            return {
                "devices_total": stats["devices_total"],
                "evaluated": stats["devices_total"] - stats["policy_unknown_count"],
                "unknown": stats["policy_unknown_count"],
            }
        return None

    async def async_added_to_hass(self) -> None:
        """Register listeners."""
        self.async_on_remove(
            async_dispatcher_connect(self.hass, self._signal, self._handle_update)
        )
        entry_data = self.hass.data.get(DOMAIN, {}).get(self._config_entry.entry_id, {})
        devices = self._config_entry.options.get("devices", {})
        for ip in devices:
            coordinator = entry_data.get(ip, {}).get("coordinator")
            if coordinator is None:
                continue
            self.async_on_remove(coordinator.async_add_listener(self._handle_update))

    @callback
    def _handle_update(self) -> None:
        """Handle dispatcher update."""
        self.async_write_ha_state()


async def async_setup_entry(hass: HomeAssistant, config_entry, async_add_entities):
    """Set up place-level sensors for a config entry."""
    entities = [
        OpenWRTPlaceSensor(
            hass=hass,
            config_entry=config_entry,
            name="Devices total",
            key="devices_total",
            entity_category=EntityCategory.DIAGNOSTIC,
            icon="mdi:router-network",
        ),
        OpenWRTPlaceSensor(
            hass=hass,
            config_entry=config_entry,
            name="Roaming enabled count",
            key="roaming_enabled_count",
            entity_category=EntityCategory.DIAGNOSTIC,
            icon="mdi:wifi-sync",
        ),
        OpenWRTPlaceSensor(
            hass=hass,
            config_entry=config_entry,
            name="Policy in sync count",
            key="policy_in_sync_count",
            entity_category=EntityCategory.DIAGNOSTIC,
            icon="mdi:check-network",
        ),
        OpenWRTPlaceSensor(
            hass=hass,
            config_entry=config_entry,
            name="Policy drift count",
            key="policy_drift_count",
            entity_category=EntityCategory.DIAGNOSTIC,
            icon="mdi:alert-network",
        ),
        OpenWRTPlaceSensor(
            hass=hass,
            config_entry=config_entry,
            name="Policy unknown count",
            key="policy_unknown_count",
            entity_category=EntityCategory.DIAGNOSTIC,
            icon="mdi:help-network",
        ),
        OpenWRTPlaceSensor(
            hass=hass,
            config_entry=config_entry,
            name="Nonstandard devices count",
            key="nonstandard_count",
            entity_category=EntityCategory.DIAGNOSTIC,
            icon="mdi:lan-pending",
        ),
        OpenWRTPlaceSensor(
            hass=hass,
            config_entry=config_entry,
            name="Nonstandard devices",
            key="nonstandard_devices",
            entity_category=EntityCategory.DIAGNOSTIC,
            icon="mdi:lan-disconnect",
        ),
        OpenWRTPlaceSensor(
            hass=hass,
            config_entry=config_entry,
            name="Wi-Fi policy last run at",
            key="wifi_policy_last_run_at",
            device_class=SensorDeviceClass.TIMESTAMP,
            entity_category=EntityCategory.DIAGNOSTIC,
        ),
        OpenWRTPlaceSensor(
            hass=hass,
            config_entry=config_entry,
            name="Wi-Fi policy last result",
            key="wifi_policy_last_result",
            entity_category=EntityCategory.DIAGNOSTIC,
            icon="mdi:check-decagram",
        ),
        OpenWRTPlaceSensor(
            hass=hass,
            config_entry=config_entry,
            name="Wi-Fi policy last success count",
            key="wifi_policy_last_success_count",
            entity_category=EntityCategory.DIAGNOSTIC,
            icon="mdi:counter",
        ),
        OpenWRTPlaceSensor(
            hass=hass,
            config_entry=config_entry,
            name="Wi-Fi policy last fail count",
            key="wifi_policy_last_fail_count",
            entity_category=EntityCategory.DIAGNOSTIC,
            icon="mdi:counter",
        ),
        OpenWRTPlaceSensor(
            hass=hass,
            config_entry=config_entry,
            name="Wi-Fi policy last error IPs",
            key="wifi_policy_last_error_ips",
            entity_category=EntityCategory.DIAGNOSTIC,
            icon="mdi:ip-network",
        ),
    ]

    async_add_entities(entities, update_before_add=True)
