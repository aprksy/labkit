"""
global_config.py purpose is to provide global configuration handler for labkit
"""
import os
from pathlib import Path
import yaml

# DEFAULT_ROOT = str(Path.home() / "workspace" / "labs")
DEFAULT_ROOT = "/home/aprksy/workspace/repo/git/project-labs/labs"
DEFAULT_CONFIG = {
    "default_root": DEFAULT_ROOT,
    "search_paths": [
        DEFAULT_ROOT,
    ],
    "default_template": "golden-arch",
    "default_vm_template": "golden-vm",
    "user": os.getenv("USER", "unknown"),
}

CONFIG_DIR = Path.home() / ".config" / "labkit"
CONFIG_FILE = CONFIG_DIR / "config.yaml"


class LabkitConfig:
    """
    LabkitConfig: class that encapsulate all the data and action for configuring
    labkit app globally
    """
    def __init__(self):
        self.data = DEFAULT_CONFIG.copy()

    def load(self):
        """Load config from disk, then apply .env overrides"""
        if CONFIG_FILE.exists():
            try:
                loaded = yaml.safe_load(CONFIG_FILE.read_text()) or {}
                # Merge lists and dicts
                if "search_paths" in loaded:
                    self.data["search_paths"] = loaded["search_paths"]
                self.data.update({
                    k: v for k, v in loaded.items()
                    if k != "search_paths"
                })
            except Exception as e:
                raise RuntimeError(f"Failed to load {CONFIG_FILE}: {e}") from e

        # Apply .env overrides
        self._apply_env_overrides()

        # Ensure search_paths is list of Path objects
        if isinstance(self.data["search_paths"], str):
            self.data["search_paths"] = [self.data["search_paths"]]
        self.data["search_paths"] = [
            Path(p).expanduser().resolve()
            for p in self.data["search_paths"]
        ]

        return self

    def _apply_env_overrides(self):
        """Override config with .env values"""
        env_mapping = {
            "LABKIT_DEFAULT_ROOT": "default_root",
            "LABKIT_SEARCH_PATHS": "search_paths",
            "LABKIT_DEFAULT_TEMPLATE": "default_template",
            "LABKIT_DEFAULT_VM_TEMPLATE": "default_vm_template",
            "LABKIT_USER": "user",
        }
        for env_key, config_key in env_mapping.items():
            if env_key in os.environ:
                value = os.environ[env_key]
                if config_key == "search_paths":
                    # Comma-separated paths
                    self.data[config_key] = [p.strip() for p in value.split(",")]
                else:
                    self.data[config_key] = value

    def save(self):
        """Save current config back to disk"""
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        data = {
            "default_root": self.data["default_root"],
            "search_paths": [str(p) for p in self.data["search_paths"]],
            "default_template": self.data["default_template"],
            "default_vm_template": self.data["default_vm_template"],
            "user": self.data["user"],
        }
        CONFIG_FILE.write_text(
            yaml.dump(data, indent=2, default_flow_style=False)
        )

    def add_search_path(self, path: Path):
        """Add a new path to search_paths if not present"""
        resolved = path.expanduser().resolve()
        if resolved not in self.data["search_paths"]:
            self.data["search_paths"].append(resolved)
            return True
        return False
