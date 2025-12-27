"""
Firstboot Handler Plugin for LabKit
Implements the EventPlugin interface for firstboot setup
"""
import logging
import subprocess
import re
from typing import Optional, Literal, List, Dict, Any
from pathlib import Path

from labkit.plugin_infra.interfaces import EventPlugin


class FirstbootHandlerPlugin(EventPlugin):
    """
    FirstbootHandlerPlugin: Regenerates SSH host keys and sets hostname on first start
    """
    
    def __init__(self):
        self.name = "firstboot-handler"
        self.version = "1.0.0"
        self.logger = logging.getLogger("firstboot-handler")
        self.interested_actions = {"instance-started"}
        self.label_key = "environment.firstboot.done"
        self.distro_types = ["alpine", "ubuntu", "debian", "centos", "rocky", "fedora", "unknown"]

    def init(self, config: Dict[str, Any], **kwargs) -> bool:
        """
        Initialize the firstboot handler plugin
        :param config: Plugin-specific configuration
        :param kwargs: Additional keyword arguments (infrastructure components)
        :return: True if initialization succeeds
        """
        try:
            # Configure logging
            log_level = config.get("log_level", "INFO")
            self.logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))

            # Get infrastructure components from kwargs
            if 'fs_writer' in kwargs:
                self.fs_writer = kwargs['fs_writer']
            if 'timer_trigger' in kwargs:
                self.timer_trigger = kwargs['timer_trigger']

            return True
        except Exception as e:
            self.logger.error(f"Failed to initialize firstboot handler: {e}")
            return False

    def get_name(self) -> str:
        """Get the name of the plugin"""
        return self.name

    def get_version(self) -> str:
        """Get the version of the plugin"""
        return self.version

    def cleanup(self) -> bool:
        """Cleanup resources when shutting down"""
        return True

    def handle_event(self, event: Dict[str, Any]) -> bool:
        """
        Handle an event from the system
        :param event: Event dictionary containing event data
        :return: True if event was handled successfully
        """
        metadata = event.get("metadata", {})
        action = metadata.get("action")
        etype = event.get("type")
        name = metadata.get("name", "unknown")

        if etype != "lifecycle" or action not in self.interested_actions:
            return True

        self.logger.info(f"Running first boot setup for {name}")

        # 1. Check if already completed
        if self.is_firstboot_done(name):
            self.logger.debug(f"First boot already completed for {name}. Skipping.")
            return True

        # 2. Detect distro
        distro = self.detect_distro(name)
        self.logger.info(f"Detected distro: {distro}")

        # 3. Regenerate SSH host keys
        if not self.regen_ssh_keys(name, distro):
            return False  # retry on next start

        # 4. Set hostname
        if not self.set_hostname(name, distro):
            return False  # retry on next boot

        # 5. Mark as complete
        self.mark_firstboot_done(name)
        self.logger.info(f"First boot setup completed for {name} ({distro})")
        
        return True

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

    def is_firstboot_done(self, name: str) -> bool:
        """Check if first boot has already been completed."""
        try:
            result = subprocess.run(
                ["incus", "config", "get", name, self.label_key],
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.returncode == 0 and result.stdout.strip() == "true"
        except Exception as e:
            self.logger.warning(f"Failed to read firstboot label from {name}: {e}")
            return False

    def detect_distro(self, name: str) -> Literal["alpine", "debian", "ubuntu", "centos", "rocky", "fedora", "unknown"]:
        """Detect container OS family from /etc/os-release."""
        try:
            # Read /etc/os-release
            cmd = ["incus", "exec", name, "--", "cat", "/etc/os-release"]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)

            if result.returncode != 0:
                self.logger.warning(f"Failed to read /etc/os-release in {name}")
                return "unknown"

            content = result.stdout.lower()

            if "alpine" in content:
                return "alpine"
            elif "ubuntu" in content:
                return "ubuntu"
            elif "debian" in content:
                return "debian"
            elif "centos" in content:
                return "centos"
            elif "rocky" in content:
                return "rocky"
            elif "fedora" in content:
                return "fedora"
            elif "cachyos" in content:
                return "cachyos"
            elif "arch" in content:
                return "arch"
            elif "void" in content:
                return "void"
            else:
                self.logger.info(f"Unknown distro for {name}: {result.stdout.splitlines()[0]}")
                return "unknown"

        except Exception as e:
            self.logger.error(f"Error detecting distro for {name}: {e}", exc_info=True)
            return "unknown"

    def regen_ssh_keys(self, name: str, distro: str) -> bool:
        """Regenerate SSH host keys if ssh-keygen is available."""
        try:
            # Check if ssh-keygen exists
            check_cmd = ["incus", "exec", name, "--", "which", "ssh-keygen"]
            result = subprocess.run(check_cmd, capture_output=True, timeout=10)
            if result.returncode != 0:
                self.logger.info(f"ssh-keygen not found in {name}, skipping SSH key regeneration.")
                return True  # Not an error — just skip

            self.logger.info(f"Regenerating SSH host keys for {name}")
            regen_cmd = [
                "incus", "exec", name, "--",
                "sh", "-c", "rm -f /etc/ssh/ssh_host_* && ssh-keygen -A -v"
            ]
            result = subprocess.run(regen_cmd, capture_output=True, text=True, timeout=30)

            if result.returncode == 0:
                self.logger.info(f"SSH host keys regenerated successfully for {name}")
                return True
            else:
                self.logger.error(f"Failed to regenerate SSH keys in {name}: {result.stderr.strip()}")
                return False

        except Exception as e:
            self.logger.error(f"Unexpected error during SSH key generation: {e}", exc_info=True)
            return False

    def set_hostname(self, name: str, distro: str) -> bool:
        """Set the container's hostname based on distro."""
        try:
            self.logger.info(f"Setting hostname to '{name}' ({distro})")

            if distro == "alpine":
                # Alpine: write /etc/hostname directly
                push_cmd = [
                    "incus", "file", "push", "--", "/dev/stdin", f"{name}/etc/hostname"
                ]
                subprocess.run(
                    push_cmd,
                    input=name,
                    capture_output=True,
                    text=True,
                    timeout=10,
                    check=True
                )
                self.logger.debug(f"Wrote /etc/hostname: {name}")

            else:
                # Systemd-based: use hostnamectl
                cmd = ["incus", "exec", name, "--", "hostnamectl", "set-hostname", name]
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)

                if result.returncode != 0:
                    self.logger.warning(f"hostnamectl failed: {result.stderr.strip()}. Falling back to /etc/hostname.")

                    # Fallback: write /etc/hostname
                    push_cmd = [
                        "incus", "file", "push", "--", "/dev/stdin", f"{name}/etc/hostname"
                    ]
                    subprocess.run(
                        push_cmd,
                        input=name,
                        capture_output=True,
                        text=True,
                        timeout=10,
                        check=True
                    )

            # Ensure /etc/hosts maps 127.0.1.1 to hostname (Debian/Ubuntu/Alpine convention)
            hosts_entry = f"127.0.1.1\t{name}"
            cmd = [
                "incus", "exec", name, "--",
                "sh", "-c", f"echo '{hosts_entry}' >> /etc/hosts"
            ]
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode != 0:
                self.logger.warning(f"Failed to update /etc/hosts: {result.stderr.strip()}")

            self.logger.info(f"Hostname set to '{name}'")
            return True

        except Exception as e:
            self.logger.error(f"Failed to set hostname in {name}: {e}", exc_info=True)
            return False

    def mark_firstboot_done(self, name: str) -> None:
        """Mark container as having completed first boot setup."""
        try:
            subprocess.run(
                ["incus", "config", "set", name, f"{self.label_key}=true"],
                check=True,
                timeout=5
            )
            self.logger.debug(f"Marked {name} as firstboot.done=true")
        except Exception as e:
            self.logger.error(f"Failed to set firstboot label on {name}: {e}")