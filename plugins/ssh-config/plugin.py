"""
SSH Config Plugin for LabKit
Implements the EventHandlerPlugin interface for SSH config updates
"""
import json
import shutil
import subprocess
import tempfile
from pathlib import Path
import logging
import threading
import time
from typing import List, Dict, Any, Optional, Dict as DictType

from labkit.plugin_infra.interfaces import EventPlugin


class SshConfigPlugin(EventPlugin):
    """
    SshConfigPlugin: Updates SSH config when containers/VMs start/stop
    """
    
    def __init__(self):
        self.name = "ssh-config"
        self.version = "1.0.0"
        self.logger = logging.getLogger("ssh-config")
        self.polling_containers: DictType[str, threading.Event] = {}
        self.polling_lock = threading.Lock()
        self.ssh_user = "labkit"
        self.ssh_key_path = Path.home() / ".ssh" / "id_ed25519"
        self.ssh_config_path = Path.home() / ".ssh" / "labkit_config"
        self.poll_interval = 0.5
        self.max_poll_attempts = 20
        self.interested_actions = {
            "instance-started",
            "instance-shutdown",
            "instance-stopped",
        }

    def init(self, config: Dict[str, Any], **kwargs) -> bool:
        """
        Initialize the SSH config plugin
        :param config: Plugin-specific configuration
        :param kwargs: Additional keyword arguments (infrastructure components)
        :return: True if initialization succeeds
        """
        try:
            # Configure from config
            self.ssh_user = config.get("ssh_user", "labkit")
            ssh_key_path_str = config.get("ssh_key_path", str(Path.home() / ".ssh" / "id_ed25519"))
            self.ssh_key_path = Path(ssh_key_path_str).expanduser()

            ssh_config_path_str = config.get("ssh_config_path", str(Path.home() / ".ssh" / "labkit_config"))
            self.ssh_config_path = Path(ssh_config_path_str).expanduser()

            self.poll_interval = config.get("poll_interval", 0.5)
            self.max_poll_attempts = config.get("max_poll_attempts", 20)

            # Get infrastructure components from kwargs
            if 'fs_writer' in kwargs:
                self.fs_writer = kwargs['fs_writer']
            if 'timer_trigger' in kwargs:
                self.timer_trigger = kwargs['timer_trigger']

            # Validate paths
            if not self.ssh_key_path.exists():
                self.logger.warning(f"SSH private key not found: {self.ssh_key_path}")
                # Try to auto-discover
                ssh_dir = Path.home() / ".ssh"
                if (ssh_dir / "aprksy").exists():
                    self.ssh_key_path = ssh_dir / "aprksy"
                elif (ssh_dir / "id_ed25519").exists():
                    self.ssh_key_path = ssh_dir / "id_ed25519"
                elif (ssh_dir / "id_rsa").exists():
                    self.ssh_key_path = ssh_dir / "id_rsa"
                else:
                    self.logger.error("No default SSH key found (~/.ssh/aprksy, id_ed25519, or id_rsa)")
                    return False

            config_parent = self.ssh_config_path.parent
            if not config_parent.exists():
                config_parent.mkdir(parents=True, exist_ok=True)

            return True
        except Exception as e:
            self.logger.error(f"Failed to initialize SSH config plugin: {e}")
            return False

    def get_name(self) -> str:
        """Get the name of the plugin"""
        return self.name

    def get_version(self) -> str:
        """Get the version of the plugin"""
        return self.version

    def cleanup(self) -> bool:
        """Cleanup resources when shutting down"""
        # Stop any ongoing polling
        for event in self.polling_containers.values():
            event.set()
        return True

    def handle_event(self, event: Dict[str, Any]) -> bool:
        """
        Handle an event from the system
        :param event: Event dictionary containing event data
        :return: True if event was handled successfully
        """
        try:
            metadata = event.get("metadata", {})
            action = metadata.get("action")
            etype = event.get("type")
            instance_name = metadata.get("name")  # Get the instance name from event

            if etype != "lifecycle" or action not in self.interested_actions:
                return True

            self.logger.info(f"Handling event {action} for instance: {instance_name}")

            # Handle instance-started events with polling for IP address
            if action == "instance-started" and instance_name:
                # Check if we're already polling this container
                with self.polling_lock:
                    if instance_name in self.polling_containers:
                        self.logger.info(f"Already polling for {instance_name}, skipping")
                        return True

                # Start polling for IP address
                stop_event = threading.Event()
                with self.polling_lock:
                    self.polling_containers[instance_name] = stop_event

                # Start polling in a separate thread
                poll_thread = threading.Thread(
                    target=self.poll_container_ip,
                    args=(instance_name, stop_event),
                    daemon=True
                )
                poll_thread.start()

                return True

            # For other events (instance-stopped, instance-shutdown), update the full config
            # Get current containers
            result = subprocess.run(["incus", "list", "--format=json"],
                                   check=True, capture_output=True, text=True)
            containers = json.loads(result.stdout)
            entries = []

            for c in containers:
                if c["status"] != "Running":
                    continue
                net = c.get("state", {}).get("network", {})
                for iface_name in ["eth0", "net0"]:
                    iface = net.get(iface_name)
                    if not iface:
                        continue
                    for addr in iface.get("addresses", []):
                        if addr["family"] == "inet" and addr["scope"] != "link":
                            entry = f"""Host {c["name"]}
  HostName {addr["address"]}
  User {self.ssh_user}
  PreferredAuthentications publickey
  IdentityFile {self.ssh_key_path}
  StrictHostKeyChecking no
  UserKnownHostsFile /dev/null
"""
                            entries.append(entry)
                            break
                    break

            # Write to SSH config using secure writer if available, otherwise direct write
            if hasattr(self, 'fs_writer') and self.fs_writer:
                success = self.fs_writer.write_file(self.ssh_config_path, "\n".join(entries) + "\n", mode=0o600)
            else:
                # Fallback to direct write with tempfile
                temp_fd = tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".tmp")
                temp_fd.write("\n".join(entries) + "\n")
                temp_fd.close()

                self.ssh_config_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(temp_fd.name, self.ssh_config_path)
                success = True

            if success:
                self.logger.info(f"Updated SSH config for {len(entries)} containers")
            else:
                self.logger.error("Failed to update SSH config")

            return success

        except subprocess.CalledProcessError as e:
            self.logger.error(f"'incus list' failed: {e}")
            return False
        except Exception as e:
            self.logger.error(f"SSH plugin error: {e}", exc_info=True)
            return False

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
        return list(self.interested_actions)

    def get_container_ip(self, container_name: str) -> str:
        """Get the IP address of a container, return empty string if not available."""
        try:
            result = subprocess.run(
                ["incus", "list", container_name, "--format=json"], 
                check=True, capture_output=True, text=True
            )
            containers = json.loads(result.stdout)
            
            for c in containers:
                if c["name"] == container_name and c["status"] == "Running":
                    net = c.get("state", {}).get("network", {})
                    for iface_name in ["eth0", "net0"]:
                        iface = net.get(iface_name)
                        if not iface:
                            continue
                        for addr in iface.get("addresses", []):
                            if addr["family"] == "inet" and addr["scope"] != "link":
                                return addr["address"]
                    break
        except subprocess.CalledProcessError:
            pass
        except Exception as e:
            self.logger.error(f"Error getting IP for {container_name}: {e}")
        
        return ""

    def update_ssh_config_for_container(self, container_name: str, ip_address: str) -> bool:
        """Update SSH config with a specific container's IP address."""
        try:
            # Read existing config to preserve other entries
            existing_entries = {}
            
            if self.ssh_config_path.exists():
                with open(self.ssh_config_path, 'r') as f:
                    content = f.read()
                    # Parse existing entries to avoid duplicates
                    lines = content.strip().split('\n\n')
                    for line_block in lines:
                        if line_block.strip() and 'Host ' in line_block:
                            # Extract hostname from the block
                            for line in line_block.split('\n'):
                                if line.strip().startswith('Host '):
                                    host_name = line.split(' ', 1)[1].strip()
                                    existing_entries[host_name] = line_block
                                    break
            
            # Add the new entry
            new_entry = f"""Host {container_name}
  HostName {ip_address}
  User {self.ssh_user}
  PreferredAuthentications publickey
  IdentityFile {self.ssh_key_path}
  StrictHostKeyChecking no
  UserKnownHostsFile /dev/null"""
            
            existing_entries[container_name] = new_entry
            
            # Write all entries to temp file then move to actual location
            all_entries = list(existing_entries.values())
            temp_fd = tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".tmp")
            temp_fd.write("\n\n".join(all_entries) + "\n")
            temp_fd.close()

            self.ssh_config_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(temp_fd.name, self.ssh_config_path)
            
            self.logger.info(f"Updated SSH config for {container_name} with IP {ip_address}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error updating SSH config for {container_name}: {e}", exc_info=True)
            return False

    def poll_container_ip(self, container_name: str, stop_event: threading.Event):
        """Poll a container until it gets an IP address or timeout occurs."""
        attempt = 0
        
        self.logger.info(f"Starting IP polling for container: {container_name}")
        
        while attempt < self.max_poll_attempts and not stop_event.is_set():
            ip_address = self.get_container_ip(container_name)
            
            if ip_address:
                self.logger.info(f"IP address found for {container_name}: {ip_address}")
                self.update_ssh_config_for_container(container_name, ip_address)
                
                # Remove from polling list
                with self.polling_lock:
                    self.polling_containers.pop(container_name, None)
                return
            
            # Wait for next poll (with exponential backoff after first few attempts)
            if attempt >= 5:  # Start exponential backoff after 5 attempts
                current_interval = min(self.poll_interval * (1.2 ** (attempt - 5)), 2.0)  # Cap at 2 seconds
            else:
                current_interval = self.poll_interval
            
            if stop_event.wait(current_interval):
                # Stop event was set, exit early
                break
            
            attempt += 1
        
        self.logger.warning(f"Timeout reached while polling IP for {container_name}")
        
        # Remove from polling list
        with self.polling_lock:
            self.polling_containers.pop(container_name, None)