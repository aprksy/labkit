# LabKit Configuration Fields Reference

This document describes all configuration fields in LabKit and their usage in the codebase.

## Global Configuration (`~/.config/labkit/config.yaml`)

### Core Settings
| Field | Type | Default | Used In | Description |
|-------|------|---------|---------|-------------|
| `default_root` | String | `~/workspace/labs` | `cli.py`, `global_config.py` | Default directory for new labs |
| `search_paths` | Array[String] | `[default_root]` | `cli.py`, `global_config.py` | Directories to search for existing labs |
| `default_template` | String | `golden-arch` | `LabConfig`, `Lab.add_node` | Default container template |
| `default_vm_template` | String | `golden-vm` | `LabConfig`, `Lab.add_node` | Default VM template |
| `default_backend` | String | `incus` | `Lab`, `cli.py` | Default backend to use |
| `user` | String | Current user | Various modules | Username for lab operations |

### Storage Settings
| Field | Type | Default | Used In | Description |
|-------|------|---------|---------|-------------|
| `shared_storage.enabled` | Boolean | `True` | `Lab.add_node` | Enable shared storage mount |
| `shared_storage.mount_point` | String | `/lab/shared` | `Lab.add_node` | Mount point for shared storage |
| `node_mount.source_dir` | String | `nodes` | `Lab.__init__` | Directory name for node configs |
| `node_mount.mount_point` | String | `/lab/node` | `Lab.add_node` | Mount point for node configs |
| `node_mount.readonly` | Boolean | `False` | `Lab.add_node` | Mount node configs as read-only |

## Lab Configuration (`lab.yaml` in lab directory)

### Basic Settings
| Field | Type | Default | Used In | Description |
|-------|------|---------|---------|-------------|
| `name` | String | `unnamed-lab` | `Lab`, `Lab.add_node` | Name of the lab |
| `template` | String | `golden-arch` | `Lab.add_node` | Default container template |
| `vm_template` | String | `golden-vm` | `Lab.add_node` | Default VM template |
| `backend` | String | `incus` | `Lab.__init__` | Backend to use for this lab |
| `user` | String | Current user | Various modules | User associated with lab |
| `managed_by` | String | `labkit` | Various modules | Tool managing this lab |

### Storage Settings (inherited from global config)
| Field | Type | Default | Used In | Description |
|-------|------|---------|---------|-------------|
| `shared_storage.enabled` | Boolean | `True` | `Lab.add_node` | Enable shared storage mount |
| `shared_storage.mount_point` | String | `/lab/shared` | `Lab.add_node` | Mount point for shared storage |
| `node_mount.source_dir` | String | `nodes` | `Lab.__init__` | Directory name for node configs |
| `node_mount.mount_point` | String | `/lab/node` | `Lab.add_node` | Mount point for node configs |
| `node_mount.readonly` | Boolean | `False` | `Lab.add_node` | Mount node configs as read-only |

## Contrib/Plugin Configuration (`~/.config/labkit/contrib_config.yaml`)

### SSH Configuration
| Field | Type | Default | Used In | Description |
|-------|------|---------|---------|-------------|
| `ssh_config.ssh_user` | String | `labkit` | `contrib/config.py` | SSH user for containers |
| `ssh_config.ssh_key_path` | String | `~/.ssh/id_ed25519` | `contrib/config.py` | Path to SSH private key |
| `ssh_config.ssh_config_path` | String | `~/.ssh/labkit_config` | `contrib/config.py` | Path to SSH config file |
| `ssh_config.log_level` | String | `INFO` | `contrib/config.py` | Logging level for SSH operations |

### Event Listener Configuration
| Field | Type | Default | Used In | Description |
|-------|------|---------|---------|-------------|
| `event_listener.event_types` | Array[String] | `["lifecycle"]` | `contrib/incus-event-listener.py` | Types of events to listen for |
| `event_listener.poll_interval` | Float | `0.5` | `contrib/plugins/ssh_config.py` | Polling interval in seconds |
| `event_listener.max_poll_attempts` | Integer | `20` | `contrib/plugins/ssh_config.py` | Max polling attempts |
| `event_listener.poll_timeout` | Integer | `10` | Not currently used | Total timeout for polling |
| `event_listener.wait_for_instance_sec` | Float | `0` | Legacy field | Legacy wait time (now using polling) |

### Firstboot Configuration
| Field | Type | Default | Used In | Description |
|-------|------|---------|---------|-------------|
| `firstboot.timeout` | Integer | `30` | Not currently used | Timeout for firstboot operations |
| `firstboot.supported_distros` | Array[String] | `["alpine", ...]` | `contrib/plugins/firstboot_handler.py` | Supported Linux distributions |

### Plugin Configuration
| Field | Type | Default | Used In | Description |
|-------|------|---------|---------|-------------|
| `plugins.ssh_config.enabled` | Boolean | `True` | `contrib/incus-event-listener.py` | Enable SSH config plugin |
| `plugins.ssh_config.ssh_options` | Object | Various | `contrib/plugins/ssh_config.py` | SSH options for generated config |
| `plugins.firstboot_handler.enabled` | Boolean | `True` | `contrib/incus-event-listener.py` | Enable firstboot handler plugin |
| `plugins.firstboot_handler.regenerate_ssh_keys` | Boolean | `True` | `contrib/plugins/firstboot_handler.py` | Regenerate SSH host keys |
| `plugins.firstboot_handler.set_hostname` | Boolean | `True` | `contrib/plugins/firstboot_handler.py` | Set hostname on first boot |
| `plugins.firstboot_handler.mark_completed` | Boolean | `True` | `contrib/plugins/firstboot_handler.py` | Mark firstboot as completed |

### Environment Configuration
| Field | Type | Default | Used In | Description |
|-------|------|---------|---------|-------------|
| `environment.development.log_level` | String | `DEBUG` | Not currently used | Log level for development |
| `environment.development.enable_plugins` | Boolean | `True` | Not currently used | Enable plugins in development |
| `environment.production.log_level` | String | `WARNING` | Not currently used | Log level for production |
| `environment.production.enable_plugins` | Boolean | `True` | Not currently used | Enable plugins in production |
| `environment.production.strict_mode` | Boolean | `True` | Not currently used | Enable strict mode in production |

### Path Configuration
| Field | Type | Default | Used In | Description |
|-------|------|---------|---------|-------------|
| `paths.plugins_dir` | String | `./contrib/plugins` | Not currently used | Directory for plugins |
| `paths.templates_dir` | String | `./contrib/templates` | Not currently used | Directory for templates |

## Environment Variables

### Global Configuration Overrides
| Environment Variable | Maps To | Used In | Description |
|---------------------|---------|---------|-------------|
| `LABKIT_DEFAULT_ROOT` | `default_root` | `global_config.py` | Override default root directory |
| `LABKIT_SEARCH_PATHS` | `search_paths` | `global_config.py` | Override search paths (comma-separated) |
| `LABKIT_DEFAULT_TEMPLATE` | `default_template` | `global_config.py` | Override default container template |
| `LABKIT_DEFAULT_VM_TEMPLATE` | `default_vm_template` | `global_config.py` | Override default VM template |
| `LABKIT_DEFAULT_BACKEND` | `default_backend` | `global_config.py` | Override default backend |
| `LABKIT_USER` | `user` | `global_config.py` | Override user |

### Plugin Configuration Overrides
| Environment Variable | Maps To | Used In | Description |
|---------------------|---------|---------|-------------|
| `LABKIT_SSH_USER` | `ssh_config.ssh_user` | `contrib/config.py` | Override SSH user |
| `LABKIT_SSH_KEY_PATH` | `ssh_config.ssh_key_path` | `contrib/config.py` | Override SSH key path |
| `LABKIT_SSH_CONFIG_PATH` | `ssh_config.ssh_config_path` | `contrib/config.py` | Override SSH config path |
| `LABKIT_SSH_LOG_LEVEL` | `ssh_config.log_level` | `contrib/config.py` | Override SSH log level |
| `LABKIT_EVENT_TYPES` | `event_listener.event_types` | `contrib/config.py` | Override event types (comma-separated) |
| `LABKIT_POLL_INTERVAL` | `event_listener.poll_interval` | `contrib/config.py` | Override poll interval |
| `LABKIT_MAX_POLL_ATTEMPTS` | `event_listener.max_poll_attempts` | `contrib/config.py` | Override max poll attempts |
| `LABKIT_POLL_TIMEOUT` | `event_listener.poll_timeout` | `contrib/config.py` | Override poll timeout |
| `LABKIT_PLUGIN_SSH_CONFIG_ENABLED` | `plugins.ssh_config.enabled` | `contrib/config.py` | Override SSH config plugin enabled |
| `LABKIT_PLUGIN_FIRSTBOOT_ENABLED` | `plugins.firstboot_handler.enabled` | `contrib/config.py` | Override firstboot handler enabled |

## Notes

### Fully Implemented Fields
Fields marked with ✓ in the "Used In" column are actively used in the codebase and affect functionality.

### Partially Implemented Fields
Some fields are defined in configuration but have limited usage:
- Many `environment` and `paths` fields are defined but not currently used in the codebase
- Some `firstboot` settings are defined but not actively used
- Some `event_listener` settings like `poll_timeout` are defined but not used

### Unused Fields
The following fields are defined in configuration but not currently used in the codebase:
- `environment.*.*` (all environment-specific settings)
- `paths.plugins_dir` and `paths.templates_dir`
- `firstboot.timeout`
- `event_listener.poll_timeout`
- Various other fields that are defined but not actively referenced in code

### Recommended Actions
1. **Document Intent**: For fields that are defined but not used, document the intended future functionality
2. **Code Implementation**: Implement functionality for fields that are meant to be used
3. **Remove Unused**: Consider removing configuration fields that are not intended to be used
4. **Feature Development**: Develop features for partially implemented configuration options