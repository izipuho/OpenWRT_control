# OpenWRT Control

This Home Assistant integration allows you to monitor and control OpenWRT-based routers over SSH. It supports checking OS version, verifying available updates, and triggering firmware updates remotely. It also lets you set device-specific configurations through selectable options.

## Features

- **Device Discovery**: Register OpenWRT routers via config flow.
- **Update Entity**: See available firmware updates and trigger upgrades.
- **Select Entity**: Change configuration type dynamically.
- **Switch Entity**: Change update type: simple or custom.
- **Text Entity**: Get IP, hostname, and OS version info.
- **Binary Sensor**: Monitor device status (online/offline).

## Installation

### HACS (Recommended)
1. Add this repository as a custom integration:
   - HACS → Integrations → 3-dot menu → Custom Repositories
   - URL: `https://github.com/izipuho/openwrt_control`
   - Category: Integration
2. Install “OpenWRT Control”.
3. Restart Home Assistant.
4. Go to Settings → Devices & Services → Integrations → Add Integration → Search for “OpenWRT Control”.

### Manual
1. Copy `custom_components/openwrt_control` to your `config/custom_components` directory.
2. Restart Home Assistant.

## Configuration

Provide SSH key you want to use for connections in consts.py. By default /config/ssh_keys/id_ed25519 is used.
Further the integration is configured via the UI. You'll need to provide:
- Device IP
- Configuration type (defined in `config_types.yaml`)

You can define config types in `config_types.yaml` like this:
```yaml
zip-3200:
  openwrt-devid: linksys:linksys_wrt3200acm
  name: WRT3200-ACM
```

## Dashboards

I wanted a glance view of my whole landscape, so I'm trying to use button-card for it. You can find template for it in `extra_files/button-card-template.yaml`. It's in early pre-alfa, but I still want to share it. Maybe someone will modify it for a better view.
![Button card example.](/extra_files/button-card-example.png)
