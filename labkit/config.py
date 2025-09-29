# labkit/config.py
import os
from pathlib import Path
import yaml

DEFAULT_CONFIG = {
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
    def __init__(self, path: Path):
        self.path = path
        self.data = DEFAULT_CONFIG.copy()

    def load(self):
        if self.path.exists():
            try:
                self.data.update(yaml.safe_load(self.path.read_text()))
            except Exception as e:
                print(f"⚠️ Failed to load lab.yaml: {e}")
        else:
            self.save()  # Create default
        return self.data

    def save(self):
        self.path.write_text(
            yaml.dump(self.data, default_flow_style=False, indent=2)
        )