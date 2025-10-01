"""
incus-event-listener: Event-Driven Automation for Incus
"""
import sys
import json
import subprocess
import importlib
from pathlib import Path
import logging
from config import Config

logging.basicConfig(
    level=getattr(logging, Config.LOG_LEVEL, logging.INFO),
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)
logger = logging.getLogger("incus-event-listener")

def load_plugins():
    plugins_dir = Path(__file__).parent / "plugins"
    sys.path.insert(0, str(plugins_dir))
    plugins = []
    for pf in plugins_dir.glob("*.py"):
        if pf.name.startswith("__") or pf.name == "example_template.py":
            continue
        modname = f"plugins.{pf.stem}"
        try:
            module = importlib.import_module(modname)
            if hasattr(module, "handle_event"):
                plugins.append(module)
                logger.info(f"Loaded plugin: {pf.stem}")
            else:
                logger.warning(f"Plugin '{modname}' missing 'handle_event(event)'")
        except Exception as e:
            logger.error(f"Failed to load plugin {modname}: {e}")
    return plugins

def main():
    logger.info("IncusLab started.")
    try:
        Config.validate()
    except Exception as e:
        logger.critical(f"Config error: {e}")
        return 1

    cmd = ["incus", "monitor", "--format=json"]
    if Config.EVENT_TYPES:
        cmd += ["--type", ",".join(Config.EVENT_TYPES)]

    try:
        with subprocess.Popen(cmd, stdout=subprocess.PIPE, text=True) as proc:
            plugins = load_plugins()
            if not plugins:
                logger.critical("No plugins loaded. Exiting.")
                return 1

            for line in proc.stdout:
                line = line.strip()
                if not line:
                    continue
                try:
                    event = json.loads(line)
                    etype = event.get("type")
                    action = event.get("metadata", {}).get("action")
                    print(f"{etype} | {action}")
                    logger.debug(f"{etype} | {action}")
                    for plugin in plugins:
                        try:
                            plugin.handle_event(event)
                        except Exception as e:
                            logger.error(f"{plugin.__name__}: {e}", exc_info=True)
                except json.JSONDecodeError:
                    logger.warning(f"Bad JSON: {line[:60]}...")
    except KeyboardInterrupt:
        logger.info("Stopped by user.")
    except FileNotFoundError:
        logger.critical("'incus' command not found. Install Incus CLI.")
        return 1
    except Exception as e:
        logger.critical(f"Unexpected: {e}", exc_info=True)
        return 1

    return 0

if __name__ == "__main__":
    sys.exit(main())