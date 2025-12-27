"""
config_manager.py: module for managing multiple configuration sources
"""
import os
from pathlib import Path
import yaml
from typing import Dict, Any, Optional
from enum import Enum

class ConfigSource(Enum):
    """Enumeration of configuration sources"""
    DEFAULTS = "defaults"
    GLOBAL_CONFIG = "global_config"  # ~/.config/labkit/config.yaml
    PROJECT_CONFIG = "project_config"  # ./lab.yaml or ./config.yaml in project
    ENVIRONMENT = "environment"  # LABKIT_* environment variables
    DOTENV = "dotenv"  # .env file in current directory
    COMMAND_LINE = "command_line"  # Command line arguments

class ConfigManager:
    """
    ConfigManager: class that manages multiple configuration sources with priority order
    """
    
    def __init__(self):
        self.sources = {}
        self.config_data = {}
        self.priority_order = [
            ConfigSource.DEFAULTS,
            ConfigSource.GLOBAL_CONFIG,
            ConfigSource.PROJECT_CONFIG,
            ConfigSource.DOTENV,
            ConfigSource.ENVIRONMENT,
            ConfigSource.COMMAND_LINE
        ]

    def load_config(self, config_source: ConfigSource = None, custom_path: str = None):
        """
        Load configuration from specified source or use default priority order
        """
        if config_source is not None:
            return self._load_single_source(config_source, custom_path)
        else:
            return self._load_with_priority()

    def _load_with_priority(self):
        """Load configuration following priority order"""
        for source in self.priority_order:
            try:
                source_config = self._load_single_source(source)
                if source_config:
                    self._merge_config(self.config_data, source_config)
            except Exception:
                # Continue to next source if current one fails
                continue
        
        return self.config_data

    def _load_single_source(self, source: ConfigSource, custom_path: str = None):
        """Load configuration from a single source"""
        if source == ConfigSource.DEFAULTS:
            return self._get_defaults()
        
        elif source == ConfigSource.GLOBAL_CONFIG:
            return self._load_global_config()
        
        elif source == ConfigSource.PROJECT_CONFIG:
            return self._load_project_config()
        
        elif source == ConfigSource.DOTENV:
            return self._load_dotenv_config()
        
        elif source == ConfigSource.ENVIRONMENT:
            return self._load_environment_config()
        
        elif source == ConfigSource.COMMAND_LINE:
            # This would be populated by command line args
            return {}
        
        return None

    def _get_defaults(self):
        """Get default configuration values"""
        return {
            "default_root": str(Path.home() / "workspace" / "labs"),
            "search_paths": [str(Path.home() / "workspace" / "labs")],
            "default_template": "golden-arch",
            "default_vm_template": "golden-vm",
            "default_backend": "incus",
            "user": os.getenv("USER", "unknown"),
            "shared_storage": {
                "enabled": True,
                "mount_point": "/lab/shared"
            },
            "node_mount": {
                "source_dir": "nodes",
                "mount_point": "/lab/node",
                "readonly": False
            }
        }

    def _load_global_config(self):
        """Load global config from ~/.config/labkit/config.yaml"""
        global_config_path = Path.home() / ".config" / "labkit" / "config.yaml"
        if global_config_path.exists():
            try:
                with open(global_config_path, 'r') as f:
                    return yaml.safe_load(f) or {}
            except Exception:
                return {}
        return {}

    def _load_project_config(self):
        """Load project-specific config from current directory"""
        project_config_paths = [
            Path.cwd() / "lab.yaml",
            Path.cwd() / "config.yaml",
            Path.cwd() / ".labkit.yaml",
            Path.cwd() / ".config.yaml"
        ]
        
        for config_path in project_config_paths:
            if config_path.exists():
                try:
                    with open(config_path, 'r') as f:
                        return yaml.safe_load(f) or {}
                except Exception:
                    continue
        return {}

    def _load_dotenv_config(self):
        """Load configuration from .env file"""
        try:
            from dotenv import load_dotenv
            dotenv_path = Path.cwd() / ".env"
            if dotenv_path.exists():
                load_dotenv(dotenv_path)
                # Extract LABKIT_* variables
                dotenv_config = {}
                for key, value in os.environ.items():
                    if key.startswith("LABKIT_"):
                        # Convert LABKIT_DEFAULT_ROOT to default_root
                        config_key = key.replace("LABKIT_", "").lower()
                        if config_key == "search_paths":
                            dotenv_config[config_key] = [p.strip() for p in value.split(",")]
                        else:
                            dotenv_config[config_key] = value
                return dotenv_config
        except ImportError:
            # python-dotenv not installed
            pass
        except Exception:
            pass
        return {}

    def _load_environment_config(self):
        """Load configuration from environment variables"""
        env_mapping = {
            "LABKIT_DEFAULT_ROOT": "default_root",
            "LABKIT_SEARCH_PATHS": "search_paths",
            "LABKIT_DEFAULT_TEMPLATE": "default_template",
            "LABKIT_DEFAULT_VM_TEMPLATE": "default_vm_template",
            "LABKIT_DEFAULT_BACKEND": "default_backend",
            "LABKIT_USER": "user",
        }
        
        env_config = {}
        for env_key, config_key in env_mapping.items():
            if env_key in os.environ:
                value = os.environ[env_key]
                if config_key == "search_paths":
                    env_config[config_key] = [p.strip() for p in value.split(",")]
                else:
                    env_config[config_key] = value
        return env_config

    def _merge_config(self, base: Dict[str, Any], update: Dict[str, Any]):
        """Merge update config into base config (nested merge)"""
        for key, value in update.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                self._merge_config(base[key], value)
            else:
                base[key] = value

    def get_config(self, key: str, default: Any = None):
        """Get a specific configuration value"""
        keys = key.split('.')
        current = self.config_data
        
        for k in keys:
            if isinstance(current, dict) and k in current:
                current = current[k]
            else:
                return default
        return current

    def set_config(self, key: str, value: Any):
        """Set a specific configuration value"""
        keys = key.split('.')
        current = self.config_data
        
        for k in keys[:-1]:
            if k not in current:
                current[k] = {}
            current = current[k]
        
        current[keys[-1]] = value

    def save_config(self, source: ConfigSource, config_data: Dict[str, Any] = None):
        """Save configuration to a specific source"""
        if config_data is None:
            config_data = self.config_data
            
        if source == ConfigSource.GLOBAL_CONFIG:
            global_config_dir = Path.home() / ".config" / "labkit"
            global_config_dir.mkdir(parents=True, exist_ok=True)
            global_config_path = global_config_dir / "config.yaml"
            with open(global_config_path, 'w') as f:
                yaml.dump(config_data, f, indent=2, default_flow_style=False)
        elif source == ConfigSource.PROJECT_CONFIG:
            project_config_path = Path.cwd() / "lab.yaml"
            with open(project_config_path, 'w') as f:
                yaml.dump(config_data, f, indent=2, default_flow_style=False)