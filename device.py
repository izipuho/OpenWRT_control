from .ssh_client import ssh_command

class Device:
    def __init__(self, ip, device_type, os, key_path="/config/ssh/id_rsa"):
        self.ip = ip
        self.device_type = device_type
        self.os = os
        self.key_path = key_path

    def get_state(self, command=None):
        if not command:
            command = "uptime" if self.os.lower() == "linux" else "echo 'Unknown OS'"
        return ssh_command(self.ip, command, self.key_path)
