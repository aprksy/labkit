"""
callable.py: Infrastructure for callable plugins that can be triggered externally
"""
import abc
import subprocess
from typing import Dict, Any, List, Optional
from pathlib import Path
import logging
import json
import threading
import queue

from .interfaces import CallablePlugin as BaseCallablePlugin


class CallablePlugin(BaseCallablePlugin):
    """
    CallablePlugin: Base class for plugins that can be called externally
    (e.g., from systemd services, cron jobs, or other external triggers)
    """

    def __init__(self, name: str, config: Dict[str, Any]):
        self.name = name
        self.config = config
        self.logger = logging.getLogger(f"plugin.callable.{name}")
        self.initialized = False

    def init(self, config: Dict[str, Any], **kwargs) -> bool:
        """
        Initialize the plugin with configuration
        :param config: Plugin-specific configuration
        :param kwargs: Additional keyword arguments (like infrastructure components)
        :return: True if initialization succeeds
        """
        try:
            self.config = config
            # Access infrastructure components if provided
            if 'fs_writer' in kwargs:
                self.fs_writer = kwargs['fs_writer']
            if 'timer_trigger' in kwargs:
                self.timer_trigger = kwargs['timer_trigger']
            self.initialized = True
            return True
        except Exception as e:
            self.logger.error(f"Failed to initialize plugin {self.name}: {e}")
            return False

    @abc.abstractmethod
    def execute(self, *args, **kwargs) -> Dict[str, Any]:
        """
        Execute the plugin with given arguments
        :param args: Positional arguments
        :param kwargs: Keyword arguments
        :return: Result dictionary
        """
        pass

    def get_name(self) -> str:
        """Get the name of the plugin"""
        return self.name

    def get_version(self) -> str:
        """Get the version of the plugin"""
        return getattr(self, 'version', '1.0.0')

    def cleanup(self) -> bool:
        """
        Cleanup resources when shutting down
        :return: True if cleanup succeeds
        """
        try:
            self.initialized = False
            return True
        except Exception as e:
            self.logger.error(f"Failed to cleanup plugin {self.name}: {e}")
            return False


class CallablePluginManager:
    """
    CallablePluginManager: Manager for callable plugins
    """

    def __init__(self):
        self.plugins: Dict[str, 'CallablePlugin'] = {}
        self.logger = logging.getLogger("plugin.manager.callable")

    def register_plugin(self, plugin: 'CallablePlugin') -> bool:
        """
        Register a callable plugin
        :param plugin: Plugin instance to register
        :return: True if registration succeeds
        """
        if plugin.name in self.plugins:
            self.logger.warning(f"Plugin {plugin.name} already registered, replacing")

        # Call the init method with config and kwargs
        if plugin.init(plugin.config):
            self.plugins[plugin.name] = plugin
            self.logger.info(f"Registered callable plugin: {plugin.name}")
            return True
        else:
            self.logger.error(f"Failed to initialize plugin {plugin.name}")
            return False

    def execute_plugin(self, plugin_name: str, *args, **kwargs) -> Optional[Dict[str, Any]]:
        """
        Execute a registered plugin
        :param plugin_name: Name of the plugin to execute
        :param args: Positional arguments
        :param kwargs: Keyword arguments
        :return: Result from plugin execution or None if plugin not found
        """
        plugin = self.plugins.get(plugin_name)
        if not plugin:
            self.logger.error(f"Plugin {plugin_name} not found")
            return None
        
        try:
            return plugin.execute(*args, **kwargs)
        except Exception as e:
            self.logger.error(f"Error executing plugin {plugin_name}: {e}")
            return None

    def list_plugins(self) -> List[str]:
        """
        List all registered callable plugins
        :return: List of plugin names
        """
        return list(self.plugins.keys())

    def unregister_plugin(self, plugin_name: str) -> bool:
        """
        Unregister a plugin
        :param plugin_name: Name of the plugin to unregister
        :return: True if unregistration succeeds
        """
        if plugin_name in self.plugins:
            plugin = self.plugins[plugin_name]
            plugin.cleanup()
            del self.plugins[plugin_name]
            self.logger.info(f"Unregistered plugin: {plugin_name}")
            return True
        return False