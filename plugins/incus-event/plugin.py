"""
Incus Event Listener Plugin for LabKit
Implements the EventHandlerPlugin interface for Incus event handling
"""
import sys
import json
import subprocess
import importlib
from pathlib import Path
import logging
from typing import List, Dict, Any, Optional

class IncusEventPlugin():
    """
    IncusEventPlugin: Handles Incus events and triggers actions
    """
    
    def __init__(self):
        self.name = "incus-event-listener"
        self.version = "1.0.0"
        self.logger = logging.getLogger("incus-event-listener")
        self.plugins = []
        self.event_types = ["lifecycle"]
        self.running = False

    def init(self, config: Dict[str, Any], labkit_config: Dict[str, Any]) -> bool:
        """
        Initialize the event listener
        :param config: Plugin-specific configuration
        :param labkit_config: Global LabKit configuration
        :return: True if initialization succeeds
        """
        try:
            # Configure logging
            log_level = config.get("log_level", "INFO")
            self.logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))
            
            # Load event types
            self.event_types = config.get("event_types", ["lifecycle"])
            
            # Load plugins
            plugins_dir = Path(__file__).parent / "plugins"
            if plugins_dir.exists():
                sys.path.insert(0, str(plugins_dir))
                for pf in plugins_dir.glob("*.py"):
                    if pf.name.startswith("__") or pf.name == "example_template.py":
                        continue
                    modname = f"plugins.{pf.stem}"
                    try:
                        module = importlib.import_module(modname)
                        if hasattr(module, "handle_event"):
                            self.plugins.append(module)
                            self.logger.info(f"Loaded plugin: {pf.stem}")
                        else:
                            self.logger.warning(f"Plugin '{modname}' missing 'handle_event(event)'")
                    except Exception as e:
                        self.logger.error(f"Failed to load plugin {modname}: {e}")
            
            # Test if Incus is available
            result = subprocess.run(["incus", "info"], capture_output=True, text=True, check=False)
            if result.returncode != 0:
                self.logger.error("Incus daemon is not running")
                return False
                
            return True
        except Exception as e:
            self.logger.error(f"Failed to initialize event listener: {e}")
            return False

    def get_name(self) -> str:
        """Get the name of the plugin"""
        return self.name

    def get_version(self) -> str:
        """Get the version of the plugin"""
        return self.version

    def cleanup(self) -> bool:
        """Cleanup resources when shutting down"""
        self.running = False
        return True

    def handle_event(self, event: Dict[str, Any]) -> bool:
        """
        Handle an event from the system
        :param event: Event dictionary containing event data
        :return: True if event was handled successfully
        """
        try:
            etype = event.get("type")
            action = event.get("metadata", {}).get("action")
            self.logger.debug(f"{etype} | {action}")
            
            for plugin in self.plugins:
                try:
                    plugin.handle_event(event)
                except Exception as e:
                    self.logger.error(f"{plugin.__name__}: {e}", exc_info=True)
            
            return True
        except Exception as e:
            self.logger.error(f"Error handling event: {e}")
            return False

    def get_event_types(self) -> List[str]:
        """
        Get list of event types this plugin wants to handle
        :return: List of event type strings
        """
        return self.event_types

    def get_actions(self) -> List[str]:
        """
        Get list of actions this plugin handles
        :return: List of action strings
        """
        # Common lifecycle actions that this plugin handles
        return [
            "instance-started",
            "instance-stopped", 
            "instance-shutdown",
            "instance-created",
            "instance-deleted"
        ]

    def start_event_monitoring(self):
        """
        Start monitoring Incus events (this would typically run in a separate thread)
        """
        cmd = ["incus", "monitor", "--format=json"]
        if self.event_types:
            cmd += ["--type", ",".join(self.event_types)]

        self.running = True
        try:
            with subprocess.Popen(cmd, stdout=subprocess.PIPE, text=True) as proc:
                if not self.plugins:
                    self.logger.critical("No plugins loaded. Exiting.")
                    return False

                for line in proc.stdout:
                    if not self.running:
                        break
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        event = json.loads(line)
                        self.handle_event(event)
                    except json.JSONDecodeError:
                        self.logger.warning(f"Bad JSON: {line[:60]}...")
        except KeyboardInterrupt:
            self.logger.info("Stopped by user.")
        except FileNotFoundError:
            self.logger.critical("'incus' command not found. Install Incus CLI.")
            return False
        except Exception as e:
            self.logger.critical(f"Unexpected: {e}", exc_info=True)
            return False

        return True