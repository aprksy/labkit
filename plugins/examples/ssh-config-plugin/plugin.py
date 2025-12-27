"""
SSH Config Plugin for LabKit
Updates SSH config when containers start/stop
"""
import json
import subprocess
import shutil
import tempfile
from pathlib import Path
import logging
from typing import Dict, Any, List

from labkit.plugin_interfaces import HookPlugin


class SSHConfigPlugin(HookPlugin):
    """
    SSHConfigPlugin: Updates SSH config when containers start/stop
    """

    def __init__(self):
        self.name = "ssh-config"
        self.version = "1.0.0"
        self.logger = logging.getLogger("plugin.ssh-config")
        self.fs_writer = None
        self.timer_trigger = None
        # Track containers that need IP polling
        self.polling_containers = {}
        self.polling_lock = threading.Lock()

    def init(self, config: Dict[str, Any], **kwargs) -> bool:
        """
        Initialize the plugin with configuration and infrastructure access
        :param config: Plugin-specific configuration
        :param kwargs: Additional keyword arguments (infrastructure components)
        :return: True if initialization succeeds
        """
        try:
            # Get infrastructure components
            self.fs_writer = kwargs.get('fs_writer')
            self.timer_trigger = kwargs.get('timer_trigger')
            
            # Get config values
            self.ssh_user = config.get("ssh_user", "labkit")
            self.ssh_key_path = Path(config.get("ssh_key_path", str(Path.home() / ".ssh" / "id_ed25519")))
            self.ssh_config_path = Path(config.get("ssh_config_path", str(Path.home() / ".ssh" / "labkit_config")))
            
            # Validate paths
            if not self.ssh_key_path.exists():
                # Try to find default keys
                ssh_dir = Path.home() / ".ssh"
                if (ssh_dir / "id_ed25519").exists():
                    self.ssh_key_path = ssh_dir / "id_ed25519"
                elif (ssh_dir / "id_rsa").exists():
                    self.ssh_key_path = ssh_dir / "id_rsa"
                else:
                    self.logger.error("No SSH key found for SSH config plugin")
                    return False

            # Add SSH config path to allowed paths if using secure writer
            if self.fs_writer:
                self.fs_writer.add_allowed_path(self.ssh_config_path.parent)
            
            return True
        except Exception as e:
            self.logger.error(f"Failed to initialize SSH config plugin: {e}")
            return False

    def get_name(self) -> str:
        """Get the name of the plugin"""
        return self.name

    def get_version(self) -> str:
        """Get the version of the plugin"""
        return self.version

    def cleanup(self) -> bool:
        """Cleanup resources when shutting down"""
        return True

    def should_execute_hook(self, command: str, phase: str, context: Dict[str, Any]) -> bool:
        """
        Determine if this plugin should execute for the given command/phase
        :param command: The CLI command being executed (e.g., 'up', 'down', 'node add')
        :param phase: Phase of the command ('pre', 'post', 'error')
        :param context: Contextual information about the operation
        :return: True if this plugin should execute
        """
        # Execute after up/down/node commands to update SSH config
        return (
            command in ["up", "down", "node add", "node remove"] and
            phase == "post"  # Run after the command completes
        )

    def execute_hook(self, command: str, phase: str, context: Dict[str, Any]) -> bool:
        """
        Execute the plugin hook after a command
        :param command: The CLI command being executed
        :param phase: Phase of the command ('pre', 'post', 'error')
        :param context: Contextual information about the operation
        :return: True if hook executed successfully
        """
        try:
            self.logger.info(f"SSH config hook triggered by: {command} ({phase})")

            # Get current containers
            result = subprocess.run(["incus", "list", "--format=json"],
                                   check=True, capture_output=True, text=True)
            containers = json.loads(result.stdout)
            entries = []

            for c in containers:
                if c["status"] != "Running":
                    continue
                net = c.get("state", {}).get("network", {})
                for iface_name in ["eth0", "net0"]:
                    iface = net.get(iface_name)
                    if not iface:
                        continue
                    for addr in iface.get("addresses", []):
                        if addr["family"] == "inet" and addr["scope"] != "link":
                            entry = f"""Host {c["name"]}
  HostName {addr["address"]}
  User {self.ssh_user}
  PreferredAuthentications publickey
  IdentityFile {self.ssh_key_path}
  StrictHostKeyChecking no
  UserKnownHostsFile /dev/null
"""
                            entries.append(entry)
                            break
                    break

            # Write to SSH config using secure writer if available, otherwise direct write
            if self.fs_writer:
                success = self.fs_writer.write_file(self.ssh_config_path, "\n".join(entries) + "\n", mode=0o600)
            else:
                # Fallback to direct write
                import tempfile
                temp_fd = tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".tmp")
                temp_fd.write("\n".join(entries) + "\n")
                temp_fd.close()

                self.ssh_config_path.parent.mkdir(parents=True, exist_ok=True)
                import shutil
                shutil.move(temp_fd.name, self.ssh_config_path)
                success = True

            if success:
                self.logger.info(f"Updated SSH config for {len(entries)} containers")
            else:
                self.logger.error("Failed to update SSH config")

            return success
        except subprocess.CalledProcessError as e:
            self.logger.error(f"'incus list' failed: {e}")
            return False
        except Exception as e:
            self.logger.error(f"SSH plugin error: {e}", exc_info=True)
            return False

    def get_hook_commands(self) -> List[str]:
        """
        Get list of commands this plugin hooks into
        :return: List of command strings (e.g., ['up', 'down', 'node add'])
        """
        return ["up", "down", "node add", "node remove"]

    def get_hook_phases(self) -> List[str]:
        """
        Get list of phases this plugin hooks into
        :return: List of phase strings ('pre', 'post', 'error')
        """
        return ["post"]