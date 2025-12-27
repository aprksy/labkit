"""
action_executor.py: Module for executing lab actions with dry-run support
"""
import subprocess
from pathlib import Path
import getpass
from datetime import datetime
from typing import List, Dict, Any, Callable
from .utils import info, success, error, run


class ActionExecutor:
    """
    ActionExecutor: Class responsible for executing action plans with dry-run support
    """
    
    def __init__(self, root: Path):
        self.root = root
        self.log_dir = root / "logs"

    def execute_actions(self, actions: List[Dict[str, Any]], dry_run: bool = False) -> bool:
        """
        Execute a list of actions with optional dry-run
        :param actions: List of action dictionaries
        :param dry_run: Whether to execute in dry-run mode
        :return: True if all actions completed successfully (or if dry_run)
        """
        if not actions:
            info("Nothing to do.")
            return True

        info("Planned actions:")
        for act in actions:
            print(f"  {act['desc']}")

        if dry_run:
            info("DRY RUN: No changes applied")
            return True

        # Apply actions
        try:
            for act in actions:
                func = act['func']
                args = act.get('args', ())
                kwargs = act.get('kwargs', {})
                
                try:
                    func(*args, **kwargs)
                except Exception as e:
                    error(f"Failed to execute: {act['desc']} → {e}")
                    raise
            success("All actions completed")
            return True
        except Exception:
            error("One or more actions failed")
            return False

    def log_event(self, action: str, **details):
        """
        Log an event to the lab's event log
        :param action: Action name
        :param details: Additional details to log
        """
        self.log_dir.mkdir(exist_ok=True)
        timestamp = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
        log_file = self.log_dir / f"{timestamp}-{action}.txt"

        data = {
            "action": action,
            "user": getpass.getuser(),
            "timestamp": timestamp,
            "lab": self.config["name"],  # This would need to be passed in
            **details
        }

        lines = [f"{k.upper()}: {v}" for k, v in data.items()]
        log_file.write_text("\n".join(lines) + "\n")