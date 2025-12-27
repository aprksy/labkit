#!/bin/sh
# Installation script for LabKit OpenRC service on Alpine Linux

set -e  # Exit on error

echo "Installing LabKit Incus Event Automation Service for OpenRC..."

# Check if running as root
if [ "$(id -u)" -ne 0 ]; then
    echo "Error: This script must be run as root"
    exit 1
fi

# Check if incus is installed
if ! command -v incus >/dev/null 2>&1; then
    echo "Error: incus is not installed. Please install incus first."
    exit 1
fi

# Check if the labkit project exists
LABKIT_DIR="/home/aprksy/workspace/homelabs/incus/labkit"
if [ ! -d "$LABKIT_DIR" ]; then
    echo "Error: LabKit directory does not exist at $LABKIT_DIR"
    echo "Please update the paths in the service file to match your installation."
    exit 1
fi

# Create service directory if it doesn't exist
SERVICE_DIR="/etc/init.d"
if [ ! -d "$SERVICE_DIR" ]; then
    echo "Error: OpenRC service directory $SERVICE_DIR does not exist"
    exit 1
fi

# Copy the service file
SERVICE_FILE="$LABKIT_DIR/contrib/openrc/incuslab-event-listener"
if [ ! -f "$SERVICE_FILE" ]; then
    echo "Error: Service file not found at $SERVICE_FILE"
    exit 1
fi

echo "Copying service file to $SERVICE_DIR/incuslab-event-listener..."
cp "$SERVICE_FILE" "$SERVICE_DIR/incuslab-event-listener"

# Make the service executable
chmod +x "$SERVICE_DIR/incuslab-event-listener"

# Check if the user exists
if ! id aprksy >/dev/null 2>&1; then
    echo "Warning: User 'aprksy' does not exist."
    echo "Please create the user or update the service file to use an existing user."
    echo "Current service file expects user 'aprksy' to exist."
    exit 1
fi

# Check if the python script exists and is executable
PYTHON_SCRIPT="$LABKIT_DIR/plugins/incus-event-listener-plugin/process_events.py"
if [ ! -f "$PYTHON_SCRIPT" ]; then
    echo "Error: Python script not found at $PYTHON_SCRIPT"
    exit 1
fi

if [ ! -x "$LABKIT_DIR/.venv/bin/python3" ]; then
    echo "Error: Python virtual environment not found at $LABKIT_DIR/.venv/bin/python3"
    exit 1
fi

# Enable the service to start at boot
echo "Enabling service to start at boot..."
rc-update add incuslab-event-listener default

# Check if the service is already running and restart if needed
if rc-service incuslab-event-listener status >/dev/null 2>&1; then
    echo "Service is currently running. Restarting..."
    rc-service incuslab-event-listener restart
else
    echo "Starting service..."
    rc-service incuslab-event-listener start
fi

# Check service status
echo "Checking service status..."
rc-service incuslab-event-listener status

echo ""
echo "Installation completed successfully!"
echo ""
echo "Service management commands:"
echo "  Start:     rc-service incuslab-event-listener start"
echo "  Stop:      rc-service incuslab-event-listener stop" 
echo "  Restart:   rc-service incuslab-event-listener restart"
echo "  Status:    rc-service incuslab-event-listener status"
echo "  Enable:    rc-update add incuslab-event-listener default"
echo "  Disable:   rc-update del incuslab-event-listener default"
echo ""
echo "Logs can be viewed with:"
echo "  journalctl -u incuslab-event-listener (if using journald)"
echo "  Or check the system logs: tail -f /var/log/messages"