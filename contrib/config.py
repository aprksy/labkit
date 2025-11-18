import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(dotenv_path=Path(__file__).parent / ".env", verbose=True)

class Config:
    SSH_USER = os.getenv("INCUSLAB_SSH_USER", "aprksy")
    SSH_KEY_PATH = Path(os.getenv("INCUSLAB_SSH_KEY_PATH", f"/home/{SSH_USER}/.ssh/aprksy"))
    SSH_CONFIG_PATH = Path(os.getenv("INCUSLAB_SSH_CONFIG_PATH", f"/home/{SSH_USER}/.ssh/incus_config"))
    LOG_LEVEL = os.getenv("INCUSLAB_LOG_LEVEL", "INFO").upper()
    EVENT_TYPES = [t.strip() for t in os.getenv("INCUSLAB_EVENT_TYPES", "lifecycle").split(",") if t.strip()]
    WAIT_FOR_INSTANCE_SEC = 5

    @classmethod
    def validate(cls):
        if not cls.SSH_KEY_PATH.exists():
            raise RuntimeError(f"SSH key not found: {cls.SSH_KEY_PATH}")
        parent = cls.SSH_CONFIG_PATH.parent
        if not parent.is_dir():
            raise RuntimeError(f"Parent dir not writable: {parent}")