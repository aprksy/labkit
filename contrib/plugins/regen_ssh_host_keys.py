"""
Regenerates SSH host keys on FIRST START of a container.
Uses an Incus label to track completion: environment.firstboot.done
"""

import logging
import subprocess
from typing import Optional

logger = logging.getLogger(__name__)

INTERESTED_ACTIONS = {"instance-started"}
LABEL_KEY = "environment.firstboot.done"

def handle_event(event) -> None:
    metadata = event.get("metadata", {})
    action = metadata.get("action")
    etype = event.get("type")
    name = metadata.get("name", "unknown")

    if etype != "lifecycle" or action not in INTERESTED_ACTIONS:
        return

    logger.info(f"Checking first boot status: {name}")

    # 1. Check if already marked as done
    try:
        result = subprocess.run(
            ["incus", "config", "get", name, LABEL_KEY],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0 and result.stdout.strip() == "true":
            logger.debug(f"First boot already completed for {name}. Skipping.")
            return
    except Exception as e:
        logger.warning(f"Failed to read label from {name}: {e}")
        return  # Be safe — don't run if we can't check

    # 2. Check if ssh-keygen is available
    try:
        check_cmd = ["incus", "exec", name, "--", "which", "ssh-keygen"]
        result = subprocess.run(check_cmd, capture_output=True, timeout=10)
        if result.returncode != 0:
            logger.info(f"ssh-keygen not found in {name}, skipping SSH key regeneration.")
            mark_done(name)
            return
    except Exception as e:
        logger.error(f"Failed to check ssh-keygen in {name}: {e}")
        return

    # 3. Regenerate SSH host keys
    try:
        logger.info(f"Regenerating SSH host keys for {name} (first boot)")
        regen_cmd = [
            "incus", "exec", name, "--",
            "sh", "-c", "rm -f /etc/ssh/ssh_host_* && ssh-keygen -A -v"
        ]
        result = subprocess.run(regen_cmd, capture_output=True, text=True, timeout=30)

        if result.returncode == 0:
            logger.info(f"Successfully regenerated SSH host keys for {name}")
            mark_done(name)
        else:
            logger.error(f"Failed to regenerate SSH keys in {name}: {result.stderr.strip()}")
            # Don't mark done — retry on next start
    except Exception as e:
        logger.error(f"Unexpected error during key generation: {e}", exc_info=True)


def mark_done(name: str) -> None:
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