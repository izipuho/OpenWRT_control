# OpenWRT Updater
[![hacs_badge](https://img.shields.io/badge/HACS-Default-orange.svg)](https://github.com/hacs/integration)

This Home Assistant integration allows you to monitor and update OpenWRT-based routers over SSH. It supports checking OS version, verifying available updates, and triggering firmware updates remotely. It also lets you set device-specific configurations through selectable options.

## Features

### Device Discovery
Register your OpenWRT devices via config flow.
### Update
- Look for available firmware updates and trigger upgrades.
- Change configuration type (device model) dynamically (will be deprecated soon)
- Select simple update with standart snapshot for your device or with custom image builder (ASU)
- Choose between force update or soft one that requires manual sysupgrade launch.
### Monitoring
Monitor device status (online/offline).

## Installation

1. Install “OpenWRT Updater” from default HACS repository or copy `custom_components/openwrt_updater` to your `config/custom_components` directory.
2. Restart Home Assistant.
3. Go to Settings → Devices & Services → Integrations → Add Integration → Search for “OpenWRT Updater”.

## Configuration

### Initial setup
Add integration via **Settings -> Devices & Services -> Add Integration -> OpenWRT Updater**.

### Global options
Set **global options** (stored in a special config entry):
- ASU base URL (default: `https://sysupgrade.openwrt.org/`)
- Base URL for downloads (default: `https://downloads.openwrt.org/`)
- SSH key path - path to the private SSH key (default: `/config/ssh_keys/id_ed25519`).
- TOH URL — URL to Table of Hardware JSON (default: `https://openwrt.org/toh.json`).
- Config types file — YAML file with device type mappings (default: `config_types.yaml`) (will be deprecated soon).
- TOH polling interval in hours — refresh interval for TOH cache.
- Device polling interval in minutes — timeout for device polling.

### Adding devices
After global options are configured, create a **Place** (config entry for grouping devices).  
Then add devices by specifying:
- Device IP
- Configuration type (list of available types is loaded from the YAML file defined in `config_types_file`).

You can define config types in `config_types_file` like this:
```yaml
zip-3200:
  openwrt-devid: linksys:linksys_wrt3200acm
  name: WRT3200-ACM
```

## Firmware Updates

The integration supports two update mechanisms, both controlled by configuration options:

### ASU mode (optional)
If ASU support is enabled and available on the device:
- The integration requests the build from ASU
- Downloads the firmware image using the callback information
- Transfers the image to the device
- Performs `sysupgrade`

### Sysupgrade overview mode
If enabled:
- The integration queries the official OpenWRT “sysupgrade overview”
- Retrieves a matching firmware entry for the device
- Downloads the referenced image
- Transfers the image to the device
- Performs `sysupgrade`

Both mechanisms are independent toggles.  
Sysupgrade overview is **not** a fallback mode: it is an explicit alternative update source.

## Dashboards

I wanted a glance view of my whole landscape, so I'm trying to use button-card for it. You can find template for it in `extra_files/button-card-template.yaml`. It's in early pre-alfa, but I still want to share it. Maybe someone will modify it for a better view.

![Button card example.](extra_files/button-card-example.png)