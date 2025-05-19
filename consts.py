DOMAIN = "openwrt_updater"

CONF_IP = "ip"
CONF_CONFIG_TYPE = "config_type"

CONFIG_TYPES_FILE = "custom_components/openwrt_updater/config_types.yaml"

SSH_KEY_PATH = "/config/ssh_keys/id_ed25519"

NAME_COMMAND = "uname -n"
VERSION_COMMAND = "cat /etc/openwrt_release | grep -oP \"(?<=RELEASE=').*?(?=')\""
INFO_COMMAND = f"{NAME_COMMAND}; {VERSION_COMMAND}"
