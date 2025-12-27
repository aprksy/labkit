"""
global_config.py purpose is to provide global configuration handler for labkit
"""
import os
from pathlib import Path
import yaml
from typing import Dict, Any

# Import the new app config
from .app_config import LabKitAppConfig

class LabkitConfig:
    """
    LabkitConfig: class that encapsulate all the data and action for configuring
    labkit app globally
    """
    def __init__(self):
        # Use the new app config class
        self.app_config = LabKitAppConfig()
        self.data = self.app_config.data

    def load(self):
        """Load config from disk, then apply .env overrides"""
        self.app_config.load()
        self.data = self.app_config.data
        return self

    def save(self):
        """Save current config back to disk"""
        self.app_config.save()

    def add_search_path(self, path: Path):
        """Add a new path to search_paths if not present"""
        return self.app_config.add_search_path(path)

    def remove_search_path(self, path: Path):
        """Remove a path from search_paths if present"""
        return self.app_config.remove_search_path(path)
