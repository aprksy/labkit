"""
Template for writing new incuslab plugins.
Copy this file to create your own action.
"""

import logging

logger = logging.getLogger(__name__)

# List of actions this plugin cares about
INTERESTED_ACTIONS = {
    "container-started",
    "container-stopped",
}

def handle_event(event):
    metadata = event.get("metadata", {})
    action = metadata.get("action")
    etype = event.get("type")

    # Filter by type and action
    if etype != "lifecycle" or action not in INTERESTED_ACTIONS:
        return

    name = metadata.get("name", "unknown")
    logger.info(f"🎯 Example plugin triggered by {action} on {name}")

    # ✅ Your custom logic here
    # - exec shell commands
    # - update files
    # - send notifications
    # - call APIs