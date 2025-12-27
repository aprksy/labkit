# LabKit OpenRC Service for Alpine Linux

This directory contains OpenRC service files and installation scripts for running the LabKit Incus Event Automation Service on Alpine Linux systems.

## Files

- `incuslab-event-listener` - OpenRC service script
- `install_service.sh` - Installation script
- `README.md` - This file

## Prerequisites

Before installing the service, ensure you have:

1. Alpine Linux installed
2. Incus installed and running
3. LabKit installed at `/home/aprksy/workspace/homelabs/incus/labkit` (or update paths as needed)
4. Python virtual environment set up in the LabKit directory
5. User `aprksy` created (or update the service file with your user)

## Installation

### Automatic Installation

1. Make sure LabKit is installed and working properly
2. Update the paths in the service file if needed (currently set for `/home/aprksy/workspace/homelabs/incus/labkit`)
3. Run the installation script as root:

```bash
sudo sh contrib/openrc/install_service.sh
```

### Manual Installation

1. Copy the service file to `/etc/init.d/`:

```bash
sudo cp contrib/openrc/incuslab-event-listener /etc/init.d/incuslab-event-listener
sudo chmod +x /etc/init.d/incuslab-event-listener
```

2. Enable the service to start at boot:

```bash
sudo rc-update add incuslab-event-listener default
```

3. Start the service:

```bash
sudo rc-service incuslab-event-listener start
```

## Configuration

The service file is configured with the following settings:

- **User/Group**: `aprksy` (update as needed)
- **Command**: Runs `incus monitor` piped to the LabKit event processor
- **Dependencies**: Requires Incus service to be running
- **Auto-restart**: Enabled

If you need to customize the installation path, edit the service file before installation:

- Update the `command_args` path to your LabKit installation
- Update the `export PATH` line with your virtual environment path
- Update the `user` and `group` if using a different user

## Service Management

Once installed, manage the service with OpenRC commands:

```bash
# Start the service
sudo rc-service incuslab-event-listener start

# Stop the service
sudo rc-service incuslab-event-listener stop

# Restart the service
sudo rc-service incuslab-event-listener restart

# Check service status
sudo rc-service incuslab-event-listener status

# Enable service at boot
sudo rc-update add incuslab-event-listener default

# Disable service at boot
sudo rc-update del incuslab-event-listener default
```

## Troubleshooting

### Service won't start

1. Check if Incus is running: `sudo rc-service incus status`
2. Verify the user exists: `id aprksy`
3. Check the service file paths are correct
4. Look at system logs: `tail -f /var/log/messages`

### Python path issues

Make sure the virtual environment path in the service file matches your LabKit installation:

- Check if `.venv/bin/python3` exists in your LabKit directory
- Verify the Python script path is correct

### Permission issues

Ensure the service user has proper permissions to:
- Access the LabKit directory
- Run Incus commands
- Write to any required directories for logs or configuration