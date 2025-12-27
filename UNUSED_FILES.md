# Unused Files Analysis - Previous Architecture

## Files Safe to Remove (Now Replaced by Plugin System)

### Old Event System Files
- `plugins/incus-event-listener.py` - Replaced by `plugins/incus-event-listener-plugin/`
- `plugins/config.py` - Replaced by plugin-specific configuration system

### Old Plugin Files (now in new plugin structure)
- `plugins/plugins/firstboot_handler.py` - Replaced by `plugins/firstboot-handler-plugin/`
- `plugins/plugins/ssh_config.py` - Replaced by `plugins/ssh-config-plugin/`
- `plugins/plugins/__init__.py` - Old plugin loader
- `plugins/plugins/*.py` - All old plugin files in the plugins/plugins directory

### Old Backend Files (to be removed after Lab class update)
- `labkit/backends/docker.py` - Will be replaced by Docker backend plugin
- `labkit/backends/qemu.py` - Will be replaced by QEMU VM plugin  
- `labkit/backends/incus.py` - Will be replaced by Incus backend plugin
- `labkit/backends/base.py` - Will be replaced by PluginInterface

## Files Still in Use (Temporary)
- `labkit/backends/*.py` - Still used by Lab class until updated to use plugin system

## Recommended Actions

### Immediate (Safe to Remove)
1. Remove entire `plugins/plugins/` directory (old plugin structure)
2. Remove `plugins/incus-event-listener.py` (old event listener)
3. Remove `plugins/config.py` (old config system)

### Later (After Lab Class Update)
1. Remove `labkit/backends/docker.py`, `qemu.py`, `incus.py`, `base.py` after updating Lab class
2. Update Lab class to use new plugin system instead of hardcoded backends

## Notes
- The systemd/ and templates/ directories contain example files that may still be useful
- The new plugin system provides the same functionality with better modularity
- Removal of old files will clean up the codebase significantly