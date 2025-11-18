"""
Regenerates SSH host keys and sets hostname on FIRST START of a container.
Supports Alpine, Ubuntu, Debian, CentOS, etc.
Uses an Incus label to track completion: environment.firstboot.done
"""

import logging
import subprocess
import re
from typing import Optional, Literal

logger = logging.getLogger(__name__)

INTERESTED_ACTIONS = {"instance-started"}
LABEL_KEY = "environment.firstboot.done"

# Supported distro families
DistroType = Literal["alpine", "debian", "ubuntu", "centos", "rocky", "fedora", "unknown"]

def handle_event(event) -> None:
    metadata = event.get("metadata", {})
    action = metadata.get("action")
    etype = event.get("type")
    name = metadata.get("name", "unknown")

    if etype != "lifecycle" or action not in INTERESTED_ACTIONS:
        return

    logger.info(f"Running first boot setup for {name}")

    # 1. Check if already completed
    if is_firstboot_done(name):
        logger.debug(f"First boot already completed for {name}. Skipping.")
        return

    # 2. Detect distro
    distro = detect_distro(name)
    logger.info(f"Detected distro: {distro}")

    # 3. Regenerate SSH host keys
    if not regen_ssh_keys(name, distro):
        return  # retry on next start

    # 4. Set hostname
    if not set_hostname(name, distro):
        return  # retry on next boot

    # 5. Mark as complete
    mark_firstboot_done(name)
    logger.info(f"First boot setup completed for {name} ({distro})")


def is_firstboot_done(name: str) -> bool:
    """Check if first boot has already been completed."""
    try:
        result = subprocess.run(
            ["incus", "config", "get", name, LABEL_KEY],
            capture_output=True,
            text=True,
            timeout=5
        )
        return result.returncode == 0 and result.stdout.strip() == "true"
    except Exception as e:
        logger.warning(f"Failed to read firstboot label from {name}: {e}")
        return False


def detect_distro(name: str) -> DistroType:
    """Detect container OS family from /etc/os-release."""
    try:
        # Read /etc/os-release
        cmd = ["incus", "exec", name, "--", "cat", "/etc/os-release"]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)

        if result.returncode != 0:
            logger.warning(f"Failed to read /etc/os-release in {name}")
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
            logger.info(f"Unknown distro for {name}: {result.stdout.splitlines()[0]}")
            return "unknown"

    except Exception as e:
        logger.error(f"Error detecting distro for {name}: {e}", exc_info=True)
        return "unknown"


def regen_ssh_keys(name: str, distro: DistroType) -> bool:
    """Regenerate SSH host keys if ssh-keygen is available."""
    try:
        # Check if ssh-keygen exists
        check_cmd = ["incus", "exec", name, "--", "which", "ssh-keygen"]
        result = subprocess.run(check_cmd, capture_output=True, timeout=10)
        if result.returncode != 0:
            logger.info(f"ssh-keygen not found in {name}, skipping SSH key regeneration.")
            return True  # Not an error — just skip

        logger.info(f"Regenerating SSH host keys for {name}")
        regen_cmd = [
            "incus", "exec", name, "--",
            "sh", "-c", "rm -f /etc/ssh/ssh_host_* && ssh-keygen -A -v"
        ]
        result = subprocess.run(regen_cmd, capture_output=True, text=True, timeout=30)

        if result.returncode == 0:
            logger.info(f"SSH host keys regenerated successfully for {name}")
            return True
        else:
            logger.error(f"Failed to regenerate SSH keys in {name}: {result.stderr.strip()}")
            return False

    except Exception as e:
        logger.error(f"Unexpected error during SSH key generation: {e}", exc_info=True)
        return False


def set_hostname(name: str, distro: DistroType) -> bool:
    """Set the container's hostname based on distro."""
    try:
        logger.info(f"Setting hostname to '{name}' ({distro})")

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
            logger.debug(f"Wrote /etc/hostname: {name}")

        else:
            # Systemd-based: use hostnamectl
            cmd = ["incus", "exec", name, "--", "hostnamectl", "set-hostname", name]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)

            if result.returncode != 0:
                logger.warning(f"hostnamectl failed: {result.stderr.strip()}. Falling back to /etc/hostname.")

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
            logger.warning(f"Failed to update /etc/hosts: {result.stderr.strip()}")

        logger.info(f"Hostname set to '{name}'")
        return True

    except Exception as e:
        logger.error(f"Failed to set hostname in {name}: {e}", exc_info=True)
        return False


def mark_firstboot_done(name: str) -> None:
    """Mark container as having completed first boot setup."""
    try:
        subprocess.run(
            ["incus", "config", "set", name, f"{LABEL_KEY}=true"],
            check=True,
            timeout=5
        )
        logger.debug(f"Marked {name} as firstboot.done=true")
    except Exception as e:
        logger.error(f"Failed to set firstboot label on {name}: {e}")