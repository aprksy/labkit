"""
app_config.py: module for handling main LabKit application configuration
"""
import os
from pathlib import Path
import yaml
from typing import Dict, Any, List
from .config_manager import ConfigManager, ConfigSource

class LabKitAppConfig:
    """
    LabKitAppConfig: class that encapsulates data and actions for configuring
    the main LabKit application
    """
    def __init__(self):
        self.data = {}
        self.config_manager = ConfigManager()

    def load(self):
        """Load app config following priority order"""
        self.data = self.config_manager.load_config()

        # Ensure search_paths is list of Path objects
        if isinstance(self.data.get("search_paths"), str):
            self.data["search_paths"] = [self.data["search_paths"]]
        elif self.data.get("search_paths") is None:
            self.data["search_paths"] = [str(Path.home() / "workspace" / "labs")]
        self.data["search_paths"] = [
            Path(p).expanduser().resolve()
            for p in self.data["search_paths"]
        ]

        return self

    def load_from_source(self, source: ConfigSource, custom_path: str = None):
        """Load config from a specific source"""
        self.data = self.config_manager._load_single_source(source, custom_path)

        # Ensure search_paths is list of Path objects
        if isinstance(self.data.get("search_paths"), str):
            self.data["search_paths"] = [self.data["search_paths"]]
        elif self.data.get("search_paths") is None:
            self.data["search_paths"] = [str(Path.home() / "workspace" / "labs")]
        self.data["search_paths"] = [
            Path(p).expanduser().resolve()
            for p in self.data["search_paths"]
        ]

        return self

    def save(self):
        """Save current config back to global config file"""
        self.config_manager.save_config(ConfigSource.GLOBAL_CONFIG, self.data)

    def add_search_path(self, path: Path):
        """Add a new path to search_paths if not present"""
        resolved = path.expanduser().resolve()
        if resolved not in self.data["search_paths"]:
            self.data["search_paths"].append(resolved)
            return True
        return False

    def remove_search_path(self, path: Path):
        """Remove a path from search_paths if present"""
        resolved = path.expanduser().resolve()
        if resolved in self.data["search_paths"]:
            self.data["search_paths"].remove(resolved)
            return True
        return False

    def get_config_value(self, key: str, default: Any = None):
        """Get a specific configuration value"""
        return self.config_manager.get_config(key, default)

    def set_config_value(self, key: str, value: Any):
        """Set a specific configuration value"""
        self.config_manager.set_config(key, value)