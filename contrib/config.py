# contrib/config.py
from pathlib import Path
import os

class Config:
    # Will be set by load()
    SSH_USER = None
    SSH_KEY_PATH = None
    SSH_CONFIG_PATH = None
    LOG_LEVEL = "INFO"
    EVENT_TYPES = ["lifecycle"]
    # Legacy config - now using polling instead of fixed wait
    WAIT_FOR_INSTANCE_SEC = 0  # Set to 0 to indicate polling is used
    # Polling configuration
    POLL_INTERVAL = 0.5  # Initial polling interval in seconds
    MAX_POLL_ATTEMPTS = 20  # Maximum number of polling attempts

    @classmethod
    def load(cls):
        """Load config from labkit's global config.yaml"""
        from labkit.global_config import LabkitConfig

        try:
            config_data = LabkitConfig().load()
        except Exception as e:
            raise RuntimeError(f"Failed to load labkit config: {e}")

        firstboot = config_data.data.get("firstboot", {})

        # 1. SSH User
        cls.SSH_USER = firstboot.get("ssh_user")
        if not cls.SSH_USER:
            # Fallback: current user
            cls.SSH_USER = os.getenv("USER", "incus-user")

        # 2. SSH Key Path
        key_path_str = firstboot.get("ssh_key_path")
        if key_path_str:
            # Expand ~ and $HOME
            key_path_str = os.path.expandvars(key_path_str)
            key_path_str = os.path.expanduser(key_path_str)
        else:
            # Auto-discover: id_ed25519 or id_rsa in ~/.ssh
            ssh_dir = Path.home() / ".ssh"
            if (ssh_dir / "id_ed25519").exists():
                key_path_str = str(ssh_dir / "id_ed25519")
            elif (ssh_dir / "id_rsa").exists():
                key_path_str = str(ssh_dir / "id_rsa")
            else:
                raise RuntimeError("No default SSH key found (~/.ssh/id_ed25519 or id_rsa)")

        cls.SSH_KEY_PATH = Path(key_path_str)

        # 3. SSH Config Path
        scp = firstboot.get("ssh_config_path")
        if scp:
            scp = os.path.expandvars(os.path.expanduser(scp))
            cls.SSH_CONFIG_PATH = Path(scp)
        else:
            cls.SSH_CONFIG_PATH = Path.home() / ".ssh" / "incus_config"

        # 4. Logging
        log_level = firstboot.get("log_level")
        if log_level:
            cls.LOG_LEVEL = log_level.upper()

        # 5. Event Types
        evt = firstboot.get("event_types")
        if isinstance(evt, str):
            cls.EVENT_TYPES = [t.strip() for t in evt.split(",") if t.strip()]
        elif isinstance(evt, list):
            cls.EVENT_TYPES = [t.strip() for t in evt if isinstance(t, str)]
        else:
            cls.EVENT_TYPES = ["lifecycle"]

        # 6. Wait Time (legacy - now using polling)
        wait = firstboot.get("wait_for_instance_sec")
        if isinstance(wait, (int, float)) and wait > 0:
            cls.WAIT_FOR_INSTANCE_SEC = float(wait)

        # 7. Polling configuration
        poll_interval = firstboot.get("poll_interval")
        if isinstance(poll_interval, (int, float)) and poll_interval > 0:
            cls.POLL_INTERVAL = float(poll_interval)

        max_attempts = firstboot.get("max_poll_attempts")
        if isinstance(max_attempts, int) and max_attempts > 0:
            cls.MAX_POLL_ATTEMPTS = max_attempts

        # Validate after load
        cls.validate()

    @classmethod
    def validate(cls):
        """Validate required paths"""
        if not cls.SSH_KEY_PATH.exists():
            raise RuntimeError(f"SSH private key not found: {cls.SSH_KEY_PATH}")

        config_parent = cls.SSH_CONFIG_PATH.parent
        if not config_parent.exists():
            raise RuntimeError(f"Parent dir does not exist: {config_parent}")
        if not os.access(config_parent, os.W_OK):
            raise RuntimeError(f"Parent dir not writable: {config_parent}")