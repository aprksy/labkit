"""
interfaces.py: Defines the interfaces that plugins should implement
"""
import abc
from typing import Dict, Any, List, Optional


class PluginInterface(abc.ABC):
    """
    PluginInterface: Base interface that all plugins must implement
    """
    
    @abc.abstractmethod
    def init(self, config: Dict[str, Any], **kwargs) -> bool:
        """
        Initialize the plugin with configuration
        :param config: Plugin-specific configuration
        :param kwargs: Additional keyword arguments (like infrastructure components)
        :return: True if initialization succeeds
        """
        pass

    @abc.abstractmethod
    def get_name(self) -> str:
        """
        Get the name of the plugin
        :return: Plugin name
        """
        pass

    @abc.abstractmethod
    def get_version(self) -> str:
        """
        Get the version of the plugin
        :return: Plugin version
        """
        pass

    @abc.abstractmethod
    def cleanup(self) -> bool:
        """
        Cleanup resources when shutting down
        :return: True if cleanup succeeds
        """
        pass


class CallablePlugin(PluginInterface):
    """
    CallablePlugin: Interface for plugins that can be called externally
    """
    
    @abc.abstractmethod
    def execute(self, *args, **kwargs) -> Dict[str, Any]:
        """
        Execute the plugin with given arguments
        :param args: Positional arguments
        :param kwargs: Keyword arguments
        :return: Result dictionary
        """
        pass


class HookPlugin(PluginInterface):
    """
    HookPlugin: Interface for plugins that hook into CLI operations
    """

    @abc.abstractmethod
    def should_execute_hook(self, command: str, phase: str, context: Dict[str, Any]) -> bool:
        """
        Determine if this plugin should execute for the given command/phase
        :param command: The CLI command being executed (e.g., 'up', 'down', 'node add')
        :param phase: Phase of the command ('pre', 'post', 'error')
        :param context: Contextual information about the operation
        :return: True if this plugin should execute
        """
        pass

    @abc.abstractmethod
    def execute_hook(self, command: str, phase: str, context: Dict[str, Any]) -> bool:
        """
        Execute the plugin hook
        :param command: The CLI command being executed
        :param phase: Phase of the command ('pre', 'post', 'error')
        :param context: Contextual information about the operation
        :return: True if hook executed successfully
        """
        pass

    @abc.abstractmethod
    def get_hook_commands(self) -> List[str]:
        """
        Get list of commands this plugin hooks into
        :return: List of command strings (e.g., ['up', 'down', 'node add'])
        """
        pass

    @abc.abstractmethod
    def get_hook_phases(self) -> List[str]:
        """
        Get list of phases this plugin hooks into
        :return: List of phase strings ('pre', 'post', 'error')
        """
        pass


class CommandPlugin(PluginInterface):
    """
    CommandPlugin: Interface for plugins that add new CLI commands
    """

    @abc.abstractmethod
    def add_cli_subcommands(self, subparsers):
        """
        Add CLI subcommands to the parser
        :param subparsers: Subparsers object from argparse
        """
        pass

    @abc.abstractmethod
    def execute_command(self, args, lab_config: Dict[str, Any]) -> bool:
        """
        Execute the plugin's command
        :param args: Arguments from CLI
        :param lab_config: Current lab configuration
        :return: True if command executed successfully
        """
        pass

    @abc.abstractmethod
    def get_command_name(self) -> str:
        """
        Get the name of the command this plugin provides
        :return: Command name string
        """
        pass


class EventPlugin(PluginInterface):
    """
    EventPlugin: Interface for plugins that handle system events
    """

    @abc.abstractmethod
    def handle_event(self, event: Dict[str, Any]) -> bool:
        """
        Handle an event from the system
        :param event: Event dictionary containing event data
        :return: True if event was handled successfully
        """
        pass

    @abc.abstractmethod
    def get_event_types(self) -> List[str]:
        """
        Get list of event types this plugin wants to handle
        :return: List of event type strings
        """
        pass

    @abc.abstractmethod
    def get_actions(self) -> List[str]:
        """
        Get list of actions this plugin handles
        :return: List of action strings
        """
        pass


class UtilityPlugin(PluginInterface):
    """
    UtilityPlugin: Interface for utility plugins that provide helper functions
    """

    @abc.abstractmethod
    def execute_utility(self, command: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a utility command
        :param command: Command to execute
        :param params: Parameters for the command
        :return: Result dictionary
        """
        pass