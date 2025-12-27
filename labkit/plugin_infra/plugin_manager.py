"""
plugin_manager.py: Central manager for the plugin infrastructure
"""
import abc
import importlib
import sys
from pathlib import Path
from typing import Dict, Any, List, Optional, Type
import logging
import yaml

from .interfaces import CallablePlugin, EventPlugin, UtilityPlugin


class PluginManager:
    """
    PluginManager: Central manager for the plugin infrastructure
    Handles loading, registering, and managing all types of plugins
    """
    
    def __init__(self, plugins_dir: Optional[Path] = None):
        self.plugins_dir = plugins_dir or Path.home() / ".labkit" / "plugins"
        self.callable_plugins = {}
        self.event_plugins = {}
        self.utility_plugins = {}
        self.logger = logging.getLogger("plugin.manager")
        
        # Infrastructure components
        self.fs_writer = None
        self.timer_trigger = None

    def load_infrastructure_components(self, config: Dict[str, Any]):
        """
        Load infrastructure components
        :param config: Configuration for infrastructure components
        """
        from .fs_writer import SecureFSWriter
        from .timer import TimerTrigger
        
        # Initialize secure filesystem writer
        fs_config = config.get("fs_writer", {})
        self.fs_writer = SecureFSWriter(fs_config)
        
        # Initialize timer trigger system
        timer_config = config.get("timer", {})
        self.timer_trigger = TimerTrigger("global_timer", timer_config)
        
        self.logger.info("Infrastructure components loaded")

    def discover_plugins(self) -> List[Path]:
        """
        Discover all available plugins in the plugins directory
        :return: List of plugin directory paths
        """
        if not self.plugins_dir.exists():
            self.logger.info(f"Plugins directory does not exist: {self.plugins_dir}")
            return []

        plugin_dirs = []
        for item in self.plugins_dir.iterdir():
            if item.is_dir() and not item.name.startswith('.'):
                # Look for plugin manifest
                manifest_path = item / "plugin.yaml"
                if manifest_path.exists():
                    plugin_dirs.append(item)
                else:
                    # Check for plugin.py as fallback
                    plugin_py_path = item / "plugin.py"
                    if plugin_py_path.exists():
                        plugin_dirs.append(item)

        self.logger.info(f"Discovered {len(plugin_dirs)} plugins in {self.plugins_dir}")
        return plugin_dirs

    def load_plugin(self, plugin_dir: Path) -> Optional[Any]:
        """
        Load a single plugin from the given directory
        :param plugin_dir: Directory containing the plugin
        :return: Loaded plugin instance or None if loading fails
        """
        try:
            # Load plugin manifest
            manifest_path = plugin_dir / "plugin.yaml"
            if not manifest_path.exists():
                self.logger.warning(f"No plugin.yaml found in {plugin_dir}")
                return None

            with open(manifest_path, 'r') as f:
                manifest = yaml.safe_load(f) or {}

            # Load plugin Python file
            plugin_py_path = plugin_dir / manifest.get("entry_point", "plugin.py")
            if not plugin_py_path.exists():
                self.logger.error(f"Plugin entry point not found: {plugin_py_path}")
                return None

            # Import the plugin module
            spec = importlib.util.spec_from_file_location(f"plugin_{plugin_dir.name}", plugin_py_path)
            if spec is None or spec.loader is None:
                self.logger.error(f"Could not create module spec for {plugin_py_path}")
                return None

            module = importlib.util.module_from_spec(spec)
            sys.modules[f"plugin_{plugin_dir.name}"] = module
            spec.loader.exec_module(module)

            # Find the plugin class in the module
            plugin_class = None
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if (isinstance(attr, type) and 
                    attr != object and 
                    issubclass(attr, (CallablePlugin, EventHandlerPlugin, UtilityPlugin))):
                    plugin_class = attr
                    break

            if plugin_class is None:
                self.logger.error(f"No valid plugin class found in {plugin_py_path}")
                return None

            # Get plugin type from manifest
            plugin_type = manifest.get("type", "utility")
            
            # Instantiate and initialize the plugin with infrastructure access
            plugin_instance = plugin_class()
            
            # Pass infrastructure components to plugin
            plugin_config = manifest.get("default_config", {})
            plugin_config.update(manifest.get("config", {}))
            
            # Initialize with infrastructure access
            init_kwargs = {
                "config": plugin_config,
                "fs_writer": self.fs_writer,
                "timer_trigger": self.timer_trigger
            }
            
            if hasattr(plugin_instance, 'init'):
                plugin_instance.init(**init_kwargs)
            else:
                # If no init method, try to pass infrastructure components directly
                if hasattr(plugin_instance, 'fs_writer'):
                    plugin_instance.fs_writer = self.fs_writer
                if hasattr(plugin_instance, 'timer_trigger'):
                    plugin_instance.timer_trigger = self.timer_trigger
                if hasattr(plugin_instance, 'config'):
                    plugin_instance.config = plugin_config

            # Register plugin based on type
            plugin_name = manifest.get("name", plugin_dir.name)
            if plugin_type == "callable":
                self.callable_plugins[plugin_name] = plugin_instance
            elif plugin_type == "event_handler":
                self.event_plugins[plugin_name] = plugin_instance
            elif plugin_type == "utility":
                self.utility_plugins[plugin_name] = plugin_instance
            else:
                # Default to utility if type is unknown
                self.utility_plugins[plugin_name] = plugin_instance

            self.logger.info(f"Successfully loaded plugin: {plugin_name} ({plugin_type})")
            return plugin_instance

        except Exception as e:
            self.logger.error(f"Error loading plugin from {plugin_dir}: {e}")
            return None

    def load_all_plugins(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Load all available plugins
        :param config: Global configuration
        :return: Dictionary of all loaded plugins
        """
        # First, load infrastructure components
        self.load_infrastructure_components(config)
        
        plugin_dirs = self.discover_plugins()
        loaded_plugins = {}

        for plugin_dir in plugin_dirs:
            plugin = self.load_plugin(plugin_dir)
            if plugin:
                # Use the plugin's own name if available, otherwise derive from directory
                plugin_name = getattr(plugin, 'name', plugin_dir.name)
                loaded_plugins[plugin_name] = plugin

        return loaded_plugins

    def get_callable_plugins(self) -> Dict[str, Any]:
        """Get all callable plugins"""
        return self.callable_plugins.copy()

    def get_event_plugins(self) -> Dict[str, Any]:
        """Get all event handler plugins"""
        return self.event_plugins.copy()

    def get_utility_plugins(self) -> Dict[str, Any]:
        """Get all utility plugins"""
        return self.utility_plugins.copy()

    def get_plugin(self, name: str) -> Optional[Any]:
        """Get a specific plugin by name"""
        # Check all plugin categories
        for plugin_dict in [self.callable_plugins, self.event_plugins, self.utility_plugins]:
            if name in plugin_dict:
                return plugin_dict[name]
        return None

    def execute_callable_plugin(self, name: str, *args, **kwargs) -> Optional[Any]:
        """
        Execute a callable plugin
        :param name: Name of the plugin to execute
        :param args: Arguments to pass to the plugin
        :param kwargs: Keyword arguments to pass to the plugin
        :return: Result from plugin execution
        """
        plugin = self.callable_plugins.get(name)
        if not plugin:
            self.logger.error(f"Callable plugin '{name}' not found")
            return None

        try:
            if hasattr(plugin, 'execute'):
                return plugin.execute(*args, **kwargs)
            else:
                self.logger.error(f"Plugin '{name}' doesn't have execute method")
                return None
        except Exception as e:
            self.logger.error(f"Error executing callable plugin '{name}': {e}")
            return None

    def handle_event(self, event: Dict[str, Any]) -> List[bool]:
        """
        Distribute an event to all interested event handler plugins
        :param event: Event dictionary
        :return: List of boolean results from each handler
        """
        results = []
        for plugin_name, plugin in self.event_plugins.items():
            # Check if plugin wants this event type
            if hasattr(plugin, 'get_event_types'):
                event_types = plugin.get_event_types()
                event_type = event.get("type")
                action = event.get("metadata", {}).get("action")
                
                if event_type in event_types or action in plugin.get_actions():
                    try:
                        result = plugin.handle_event(event)
                        results.append(result)
                        self.logger.debug(f"Event handled by {plugin_name}: {result}")
                    except Exception as e:
                        self.logger.error(f"Error in {plugin_name} handling event: {e}")
                        results.append(False)
            else:
                # If plugin doesn't have get_event_types, try to handle anyway
                try:
                    result = plugin.handle_event(event)
                    results.append(result)
                    self.logger.debug(f"Event handled by {plugin_name}: {result}")
                except Exception as e:
                    self.logger.error(f"Error in {plugin_name} handling event: {e}")
                    results.append(False)

        return results

    def cleanup(self):
        """Cleanup all plugins and infrastructure components"""
        # Cleanup plugins
        all_plugins = {**self.callable_plugins, **self.event_plugins, **self.utility_plugins}
        for name, plugin in all_plugins.items():
            if hasattr(plugin, 'cleanup'):
                try:
                    plugin.cleanup()
                except Exception as e:
                    self.logger.error(f"Error cleaning up plugin {name}: {e}")

        # Cleanup infrastructure components
        if self.timer_trigger:
            self.timer_trigger.cleanup()