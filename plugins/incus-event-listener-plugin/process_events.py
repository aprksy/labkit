#!/usr/bin/env python3
"""
process_events.py: Simple event processor that receives incus monitor output and triggers appropriate actions
"""
import sys
import json
import logging
import subprocess
from pathlib import Path
import os

# Add the labkit root to path so we can import modules
LABKIT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(LABKIT_ROOT))

from labkit.plugin_manager import PluginManager
from labkit.global_config import LabkitConfig


def setup_logging():
    """Setup logging for the event processor"""
    log_level = os.environ.get("LOG_LEVEL", "INFO")
    logging.basicConfig(
        level=getattr(logging, log_level, logging.INFO),
        format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
    )


def main():
    """Main function to process events from stdin"""
    setup_logging()
    logger = logging.getLogger("incus-event-processor")
    
    # Load configuration and initialize plugin manager
    try:
        config = LabkitConfig().load()
        plugin_manager = PluginManager()
        plugin_manager.load_infrastructure(config.data)
        plugin_manager.load_all_plugins(config.data)
        
        # Get event handler plugins
        event_plugins = plugin_manager.get_event_plugins()
        logger.info(f"Loaded {len(event_plugins)} event handler plugins")
        
        if not event_plugins:
            logger.warning("No event handler plugins loaded")
            return 1
            
    except Exception as e:
        logger.error(f"Failed to initialize: {e}")
        return 1
    
    # Process events from stdin (piped from incus monitor)
    logger.info("Starting event processing from stdin...")
    
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
            
        try:
            event = json.loads(line)
            
            # Distribute event to all interested plugins
            for plugin_name, plugin in event_plugins.items():
                try:
                    # Check if this plugin is interested in this event
                    interested_event_types = plugin.get_event_types()
                    interested_actions = plugin.get_actions()
                    
                    event_type = event.get("type", "unknown")
                    action = event.get("metadata", {}).get("action", "unknown")
                    
                    if (event_type in interested_event_types or 
                        action in interested_actions):
                        
                        success = plugin.handle_event(event)
                        if success:
                            logger.debug(f"Event handled by {plugin_name}")
                        else:
                            logger.warning(f"Plugin {plugin_name} failed to handle event")
                            
                except Exception as e:
                    logger.error(f"Error in {plugin_name} handling event: {e}", exc_info=True)
                    
        except json.JSONDecodeError:
            logger.warning(f"Invalid JSON received: {line[:60]}...")
        except KeyboardInterrupt:
            logger.info("Interrupted by user")
            break
        except Exception as e:
            logger.error(f"Error processing event: {e}", exc_info=True)
    
    # Cleanup
    plugin_manager.cleanup()
    logger.info("Event processing completed")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())