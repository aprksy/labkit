"""
Incus Event Listener Plugin for LabKit
Listens to Incus events and triggers appropriate actions
"""
import subprocess
import json
import threading
import queue
import logging
from typing import Dict, Any, List, Optional
from pathlib import Path
import time
import signal
import sys

from labkit.plugin_infra.interfaces import EventPlugin


class IncusEventListenerPlugin(EventPlugin):
    """
    IncusEventListenerPlugin: Listens to Incus lifecycle events and triggers actions
    """
    
    def __init__(self):
        self.name = "incus-event-listener"
        self.version = "1.0.0"
        self.logger = logging.getLogger("plugin.incus-event-listener")
        self.running = False
        self.event_queue = queue.Queue()
        self.monitor_process = None
        self.event_handlers = []
        self.labkit_config = {}
        
    def init(self, config: Dict[str, Any], labkit_config: Dict[str, Any]) -> bool:
        """
        Initialize the event listener plugin
        :param config: Plugin-specific configuration
        :param labkit_config: Global LabKit configuration
        :return: True if initialization succeeds
        """
        try:
            self.labkit_config = labkit_config
            
            # Set up logging
            log_level = config.get("log_level", "INFO")
            self.logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))
            
            # Set up event types to listen for
            self.event_types = config.get("event_types", ["lifecycle"])
            
            # Validate Incus is available
            result = subprocess.run(["incus", "info"], capture_output=True, text=True, check=False)
            if result.returncode != 0:
                self.logger.error("Incus is not available or not running")
                return False
                
            return True
        except Exception as e:
            self.logger.error(f"Failed to initialize Incus event listener: {e}")
            return False

    def get_name(self) -> str:
        """Get the name of the plugin"""
        return self.name

    def get_version(self) -> str:
        """Get the version of the plugin"""
        return self.version

    def cleanup(self) -> bool:
        """Cleanup resources when shutting down"""
        self.stop_monitoring()
        return True

    def handle_event(self, event: Dict[str, Any]) -> bool:
        """
        Handle an incoming event
        :param event: Event dictionary containing event data
        :return: True if event was handled successfully
        """
        try:
            event_type = event.get("type", "unknown")
            metadata = event.get("metadata", {})
            action = metadata.get("action", "unknown")
            name = metadata.get("name", "unknown")

            self.logger.info(f"Received event: {event_type} | {action} | {name}")
            
            # Process the event
            self.process_event(event)
            return True
        except Exception as e:
            self.logger.error(f"Error handling event: {e}", exc_info=True)
            return False

    def process_event(self, event: Dict[str, Any]):
        """
        Process an event and trigger appropriate handlers
        :param event: Event dictionary
        """
        metadata = event.get("metadata", {})
        action = metadata.get("action")
        name = metadata.get("name", "unknown")
        
        # Only process lifecycle events for instance-started/instance-stopped/instance-deleted
        if event.get("type") == "lifecycle" and action in ["instance-started", "instance-stopped", "instance-deleted"]:
            # Queue the event for processing by registered handlers
            self.event_queue.put(event)

    def start_monitoring(self):
        """
        Start monitoring Incus events in a background process
        """
        if self.running:
            return True
            
        try:
            # Build the incus monitor command
            cmd = ["incus", "monitor", "--format=json"]
            if self.event_types:
                cmd.extend(["--type", ",".join(self.event_types)])

            self.logger.info(f"Starting Incus event monitoring with command: {' '.join(cmd)}")
            
            # Start the monitor process
            self.monitor_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
                universal_newlines=True
            )
            
            self.running = True
            
            # Start event processing thread
            self.event_thread = threading.Thread(target=self._event_processing_loop, daemon=True)
            self.event_thread.start()
            
            self.logger.info("Incus event monitoring started")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to start Incus event monitoring: {e}")
            return False

    def stop_monitoring(self):
        """
        Stop monitoring Incus events
        """
        if not self.running:
            return True
            
        self.running = False
        
        if self.monitor_process:
            try:
                self.monitor_process.terminate()
                self.monitor_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.monitor_process.kill()
            except Exception:
                pass  # Process may already be dead
            finally:
                self.monitor_process = None
        
        self.logger.info("Incus event monitoring stopped")

    def _event_processing_loop(self):
        """
        Internal method to process events from the monitor process
        """
        if not self.monitor_process or not self.monitor_process.stdout:
            return
            
        try:
            for line in iter(self.monitor_process.stdout.readline, ''):
                if not self.running:
                    break
                    
                line = line.strip()
                if not line:
                    continue
                    
                try:
                    event = json.loads(line)
                    self.handle_event(event)
                except json.JSONDecodeError:
                    self.logger.warning(f"Invalid JSON received: {line[:60]}...")
                except Exception as e:
                    self.logger.error(f"Error processing event line: {e}", exc_info=True)
                    
        except Exception as e:
            self.logger.error(f"Error in event processing loop: {e}", exc_info=True)
        finally:
            if self.monitor_process:
                self.monitor_process.stdout.close()

    def get_event_types(self) -> List[str]:
        """
        Get list of event types this plugin wants to handle
        :return: List of event type strings
        """
        return ["lifecycle"]

    def get_actions(self) -> List[str]:
        """
        Get list of actions this plugin handles
        :return: List of action strings
        """
        return ["instance-started", "instance-stopped", "instance-deleted"]

    def register_event_handler(self, handler_func):
        """
        Register a function to handle events
        :param handler_func: Function that takes an event dict as parameter
        """
        self.event_handlers.append(handler_func)

    def deregister_event_handler(self, handler_func):
        """
        Remove a registered event handler
        :param handler_func: Function to remove
        """
        if handler_func in self.event_handlers:
            self.event_handlers.remove(handler_func)