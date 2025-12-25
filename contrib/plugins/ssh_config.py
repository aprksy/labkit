import json
import shutil
import subprocess
import tempfile
from pathlib import Path
import logging
import threading
import time
from typing import Dict, Set
from config import Config

logger = logging.getLogger(__name__)

INTERESTED_ACTIONS = {
    "instance-started",
    "instance-shutdown",
    "instance-stopped",
}

# Track containers that need IP polling
polling_containers: Dict[str, threading.Event] = {}
polling_lock = threading.Lock()

def get_container_ip(container_name: str) -> str:
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
        logger.error(f"Error getting IP for {container_name}: {e}")

    return ""

def update_ssh_config_for_container(container_name: str, ip_address: str) -> bool:
    """Update SSH config with a specific container's IP address."""
    try:
        # Read existing config to preserve other entries
        config_path = Path(Config.SSH_CONFIG_PATH)
        existing_entries = {}

        if config_path.exists():
            with open(config_path, 'r') as f:
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
  User {Config.SSH_USER}
  PreferredAuthentications publickey
  IdentityFile {Config.SSH_KEY_PATH}
  StrictHostKeyChecking no
  UserKnownHostsFile /dev/null"""

        existing_entries[container_name] = new_entry

        # Write all entries to temp file then move to actual location
        all_entries = list(existing_entries.values())
        temp_fd = tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".tmp")
        temp_fd.write("\n\n".join(all_entries) + "\n")
        temp_fd.close()

        config_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(temp_fd.name, config_path)

        logger.info(f"Updated SSH config for {container_name} with IP {ip_address}")
        return True

    except Exception as e:
        logger.error(f"Error updating SSH config for {container_name}: {e}", exc_info=True)
        return False

def poll_container_ip(container_name: str, stop_event: threading.Event):
    """Poll a container until it gets an IP address or timeout occurs."""
    max_attempts = 20  # Total attempts before giving up (e.g., 10 seconds with 0.5s intervals)
    poll_interval = 0.5  # Initial polling interval in seconds
    attempt = 0

    logger.info(f"Starting IP polling for container: {container_name}")

    while attempt < max_attempts and not stop_event.is_set():
        ip_address = get_container_ip(container_name)

        if ip_address:
            logger.info(f"IP address found for {container_name}: {ip_address}")
            update_ssh_config_for_container(container_name, ip_address)

            # Remove from polling list
            with polling_lock:
                polling_containers.pop(container_name, None)
            return

        # Wait for next poll (with exponential backoff after first few attempts)
        if attempt >= 5:  # Start exponential backoff after 5 attempts
            current_interval = min(poll_interval * (1.2 ** (attempt - 5)), 2.0)  # Cap at 2 seconds
        else:
            current_interval = poll_interval

        if stop_event.wait(current_interval):
            # Stop event was set, exit early
            break

        attempt += 1

    logger.warning(f"Timeout reached while polling IP for {container_name}")

    # Remove from polling list
    with polling_lock:
        polling_containers.pop(container_name, None)

def handle_event(event):
    metadata = event.get("metadata", {})
    action = metadata.get("action")
    etype = event.get("type")
    container_name = metadata.get("name", "")

    if etype != "lifecycle" or action not in INTERESTED_ACTIONS:
        return

    if action == "instance-started":
        logger.info(f"Detected container start: {container_name}")

        # Check if container already has an IP immediately
        ip_address = get_container_ip(container_name)
        if ip_address:
            logger.info(f"Container {container_name} already has IP: {ip_address}")
            update_ssh_config_for_container(container_name, ip_address)
        else:
            # Start polling for IP address
            with polling_lock:
                if container_name not in polling_containers:
                    stop_event = threading.Event()
                    polling_containers[container_name] = stop_event
                    # Start polling thread
                    thread = threading.Thread(
                        target=poll_container_ip,
                        args=(container_name, stop_event),
                        daemon=True
                    )
                    thread.start()
                    logger.info(f"Started IP polling thread for {container_name}")

    elif action in ["instance-shutdown", "instance-stopped"]:
        logger.info(f"Detected container stop: {container_name}")

        # Stop polling if the container is being stopped
        with polling_lock:
            if container_name in polling_containers:
                stop_event = polling_containers[container_name]
                stop_event.set()
                logger.info(f"Stopped IP polling for {container_name}")

        # Update SSH config to remove the container entry
        try:
            config_path = Path(Config.SSH_CONFIG_PATH)
            if config_path.exists():
                with open(config_path, 'r') as f:
                    content = f.read()

                # Remove the specific container entry
                lines = content.strip().split('\n\n')
                updated_lines = []

                skip_next = False
                for line_block in lines:
                    if skip_next:
                        skip_next = False
                        continue

                    if line_block.strip() and f"Host {container_name}\n" in line_block:
                        # Skip this block (the container entry to be removed)
                        continue
                    else:
                        updated_lines.append(line_block)

                # Write updated config
                if updated_lines:
                    temp_fd = tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".tmp")
                    temp_fd.write("\n\n".join(updated_lines) + "\n")
                    temp_fd.close()
                    shutil.move(temp_fd.name, config_path)
                    logger.info(f"Removed {container_name} from SSH config")
                else:
                    # If no entries left, just remove the file
                    config_path.unlink(missing_ok=True)
                    logger.info(f"Removed SSH config file (no entries left)")

        except Exception as e:
            logger.error(f"Error updating SSH config after container stop: {e}", exc_info=True)
