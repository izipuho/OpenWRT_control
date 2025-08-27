# OpenWRT Updater
[![hacs_badge](https://img.shields.io/badge/HACS-Default-orange.svg)](https://github.com/hacs/integration)

This Home Assistant integration allows you to monitor and update OpenWRT-based routers over SSH. It supports checking OS version, verifying available updates, and triggering firmware updates remotely. It also lets you set device-specific configurations through selectable options.

## Features

### Device Discovery
Register your OpenWRT devices via config flow.
### Update
- See available firmware updates and trigger upgrades.
- Change configuration type (device model) dynamically.
- Select simple update with standart snapshot for your device or with custom image builder
- Choose between force update or soft one that requires manual sysupgrade launch.
### Monitoring
Monitor device status (online/offline).