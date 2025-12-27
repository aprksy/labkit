"""
contrib_config.py: module for handling LabKit contrib/plugin configuration
"""
import os
from pathlib import Path
import yaml
from typing import Dict, Any, List, Optional
from .config_manager import ConfigManager, ConfigSource

class LabKitContribConfig:
    """
    LabKitContribConfig: class that encapsulates data and actions for configuring
    LabKit contrib/plugins
    """
    def __init__(self):
        self.data = {}
        self.config_manager = ConfigManager()

    def load(self):
        """Load contrib config following priority order"""
        # Load the main config first and then extract contrib-specific parts
        full_config = self.config_manager.load_config()

        # Extract contrib-specific parts
        self.data = {
            "ssh_config": full_config.get("ssh_config", {
                "ssh_user": "labkit",
                "ssh_key_path": str(Path.home() / ".ssh" / "id_ed25519"),
                "ssh_config_path": str(Path.home() / ".ssh" / "labkit_config"),
                "log_level": "INFO"
            }),
            "event_listener": full_config.get("event_listener", {
                "event_types": ["lifecycle"],
                "poll_interval": 0.5,
                "max_poll_attempts": 20,
                "poll_timeout": 10,
                "wait_for_instance_sec": 0
            }),
            "firstboot": full_config.get("firstboot", {
                "timeout": 30,
                "supported_distros": [
                    "alpine", "ubuntu", "debian", "centos", "rocky", "fedora"
                ]
            }),
            "plugins": full_config.get("plugins", {
                "ssh_config": {
                    "enabled": True,
                    "ssh_options": {
                        "PreferredAuthentications": "publickey",
                        "StrictHostKeyChecking": "no",
                        "UserKnownHostsFile": "/dev/null",
                        "LogLevel": "ERROR"
                    }
                },
                "firstboot_handler": {
                    "enabled": True,
                    "regenerate_ssh_keys": True,
                    "set_hostname": True,
                    "mark_completed": True
                }
            }),
            "environment": full_config.get("environment", {
                "development": {
                    "log_level": "DEBUG",
                    "enable_plugins": True
                },
                "production": {
                    "log_level": "WARNING",
                    "enable_plugins": True,
                    "strict_mode": True
                }
            }),
            "paths": full_config.get("paths", {
                "plugins_dir": "./contrib/plugins",
                "templates_dir": "./contrib/templates"
            })
        }

        # Validate paths
        self._validate_paths()

        return self

    def load_from_source(self, source: ConfigSource, custom_path: str = None):
        """Load contrib config from a specific source"""
        full_config = self.config_manager._load_single_source(source, custom_path)

        # Extract contrib-specific parts
        self.data = {
            "ssh_config": full_config.get("ssh_config", {
                "ssh_user": "labkit",
                "ssh_key_path": str(Path.home() / ".ssh" / "id_ed25519"),
                "ssh_config_path": str(Path.home() / ".ssh" / "labkit_config"),
                "log_level": "INFO"
            }),
            "event_listener": full_config.get("event_listener", {
                "event_types": ["lifecycle"],
                "poll_interval": 0.5,
                "max_poll_attempts": 20,
                "poll_timeout": 10,
                "wait_for_instance_sec": 0
            }),
            "firstboot": full_config.get("firstboot", {
                "timeout": 30,
                "supported_distros": [
                    "alpine", "ubuntu", "debian", "centos", "rocky", "fedora"
                ]
            }),
            "plugins": full_config.get("plugins", {
                "ssh_config": {
                    "enabled": True,
                    "ssh_options": {
                        "PreferredAuthentications": "publickey",
                        "StrictHostKeyChecking": "no",
                        "UserKnownHostsFile": "/dev/null",
                        "LogLevel": "ERROR"
                    }
                },
                "firstboot_handler": {
                    "enabled": True,
                    "regenerate_ssh_keys": True,
                    "set_hostname": True,
                    "mark_completed": True
                }
            }),
            "environment": full_config.get("environment", {
                "development": {
                    "log_level": "DEBUG",
                    "enable_plugins": True
                },
                "production": {
                    "log_level": "WARNING",
                    "enable_plugins": True,
                    "strict_mode": True
                }
            }),
            "paths": full_config.get("paths", {
                "plugins_dir": "./contrib/plugins",
                "templates_dir": "./contrib/templates"
            })
        }

        # Validate paths
        self._validate_paths()

        return self

    def _validate_paths(self):
        """Validate that required paths exist"""
        ssh_key_path = Path(self.data["ssh_config"]["ssh_key_path"])
        if not ssh_key_path.exists():
            # Try to find default keys
            default_keys = [
                Path.home() / ".ssh" / "id_ed25519",
                Path.home() / ".ssh" / "id_rsa"
            ]
            for key_path in default_keys:
                if key_path.exists():
                    self.data["ssh_config"]["ssh_key_path"] = str(key_path)
                    break

        ssh_config_parent = Path(self.data["ssh_config"]["ssh_config_path"]).parent
        if not ssh_config_parent.exists():
            raise RuntimeError(f"SSH config parent directory does not exist: {ssh_config_parent}")

    def save(self):
        """Save current contrib config back to disk"""
        # This would save to the global contrib config file
        contrib_config_dir = Path.home() / ".config" / "labkit"
        contrib_config_dir.mkdir(parents=True, exist_ok=True)
        contrib_config_file = contrib_config_dir / "contrib_config.yaml"

        contrib_config_file.write_text(
            yaml.dump(self.data, indent=2, default_flow_style=False)
        )

    def is_plugin_enabled(self, plugin_name: str) -> bool:
        """Check if a specific plugin is enabled"""
        if plugin_name == "ssh_config":
            return self.data["plugins"]["ssh_config"]["enabled"]
        elif plugin_name == "firstboot_handler":
            return self.data["plugins"]["firstboot_handler"]["enabled"]
        return False

    def get_plugin_config(self, plugin_name: str) -> Optional[Dict[str, Any]]:
        """Get configuration for a specific plugin"""
        if plugin_name == "ssh_config":
            return self.data["plugins"]["ssh_config"]
        elif plugin_name == "firstboot_handler":
            return self.data["plugins"]["firstboot_handler"]
        return None

    def get_ssh_config(self) -> Dict[str, Any]:
        """Get SSH configuration"""
        return self.data["ssh_config"]

    def get_event_listener_config(self) -> Dict[str, Any]:
        """Get event listener configuration"""
        return self.data["event_listener"]