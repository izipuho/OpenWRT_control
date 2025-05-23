# OpenWRT Control

This Home Assistant integration allows you to monitor and control OpenWRT-based routers over SSH. It supports checking OS version, verifying available updates, and triggering firmware updates remotely. It also lets you set device-specific configurations through selectable options.

## Features

- **Device Discovery**: Register OpenWRT routers via config flow.
- **Update Entity**: See available firmware updates and trigger upgrades.
- **Select Entity**: Change configuration type dynamically.
- **Text Entity**: Get IP, hostname, and OS version info.
- **Binary Sensor**: Monitor device status (online/offline).
