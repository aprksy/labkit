import json
import shutil
import subprocess
import tempfile
from pathlib import Path
import logging
import time
from config import Config

logger = logging.getLogger(__name__)

INTERESTED_ACTIONS = {
    "instance-started",
    "instance-shutdown",
    "instance-stopped",
}

def handle_event(event):
    metadata = event.get("metadata", {})
    action = metadata.get("action")
    etype = event.get("type")

    if etype != "lifecycle" or action not in INTERESTED_ACTIONS:
        return

    time.sleep(Config.WAIT_FOR_INSTANCE_SEC)
    logger.info(f"Updating SSH config due to: {action}")
    try:
        result = subprocess.run(["incus", "list", "--format=json"], check=True, capture_output=True, text=True)
        containers = json.loads(result.stdout)
        entries = []

        print(f"container count: {len(containers)}")
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
  User {Config.SSH_USER}
  PreferredAuthentications publickey
  IdentityFile {Config.SSH_KEY_PATH}
  # StrictHostKeyChecking yes
  # UserKnownHostsFile /dev/null
"""
                        entries.append(entry)
                        break
                break

        temp_fd = tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".tmp")
        temp_fd.write("\n".join(entries) + "\n")
        temp_fd.close()

        config_path = Path(Config.SSH_CONFIG_PATH)
        config_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(temp_fd.name, config_path)
        logger.info(f"Updated SSH config for {len(entries)} containers")

    except subprocess.CalledProcessError as e:
        logger.error(f"'incus list' failed: {e}")
    except Exception as e:
        logger.error(f"SSH plugin error: {e}", exc_info=True)