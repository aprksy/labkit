"""
config.py: module for handling homelab configuration 
"""
import os
from pathlib import Path
import yaml

# Define non-direct user-needs here, override will come from cmd args
DEFAULT_LAB_CONFIG = {
    "name": "unnamed-lab",
    "template": "golden-image",
    "network_mode": "shared",  # 'shared' or later 'isolated'
    "shared_storage": {
        "enabled": True,
        "mount_point": "/lab/shared"
    },
    "node_mount": {
        "source_dir": "nodes",
        "mount_point": "/lab/node",
        "readonly": False
    },
    "user": os.getenv("SUDO_USER") or os.getenv("USER", "unknown"),
    "managed_by": "labkit"
}

class LabConfig:
    """
    LabConfig: class that encapsulate all the data and action for configuring
    homelab using Incus containers
    """
    def __init__(self, path: Path):
        self.path = path
        self.data = DEFAULT_LAB_CONFIG.copy()

    def load(self):
        """
        load: loads configuration from default lab.yaml
        """
        if self.path.exists():
            try:
                self.data.update(yaml.safe_load(self.path.read_text()))
            except Exception as e:
                raise RuntimeError(f"Failed to load lab.yaml: {e}") from e
        else:
            self.save()  # Create default
        return self.data

    def save(self):
        """
        save: saves configuration to lab.yaml
        """
        self.path.write_text(
            yaml.dump(self.data, default_flow_style=False, indent=2)
        )
