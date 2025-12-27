import subprocess
import json
import os
from pathlib import Path
from typing import List, Optional
from ..models import RequiredNode, NodeType
from .base import NodeBackend
from ..utils import run

class QemuNodeBackend(NodeBackend):
    def __init__(self, lab_name: str, storage_path: str = None):
        self.lab_prefix = f"{lab_name}"
        self.storage_path = Path(storage_path or f"/var/lib/labkit/vms/{lab_name}")
        self.storage_path.mkdir(parents=True, exist_ok=True)

    def _vm_name(self, logical_name: str) -> str:
        return f"{self.lab_prefix}-{logical_name}"

    def _logical_name(self, vm_name: str) -> str:
        """Extract logical name from VM name"""
        if vm_name.startswith(f"{self.lab_prefix}-"):
            return vm_name[len(self.lab_prefix)+1:]
        return vm_name

    def _vm_config_path(self, node_name: str) -> Path:
        return self.storage_path / f"{node_name}.json"

    def _get_vm_pid_file(self, node_name: str) -> Path:
        return self.storage_path / f"{node_name}.pid"

    def provision(self, node: RequiredNode) -> None:
        vm_name = self._vm_name(node.name)
        vm_config_path = self._vm_config_path(node.name)
        
        # Create disk image if needed
        disk_path = self.storage_path / f"{node.name}.qcow2"
        if not disk_path.exists():
            # Create a qcow2 disk image
            run(["qemu-img", "create", "-f", "qcow2", str(disk_path), node.disk], check=True)
        
        # Prepare the VM configuration
        vm_config = {
            "name": vm_name,
            "image": node.image,  # This should be an ISO or existing disk
            "cpus": node.cpus,
            "memory": node.memory,
            "disk": str(disk_path),
            "network": "user",  # Default network mode
            "config": node.config
        }
        
        # Save configuration
        vm_config_path.write_text(json.dumps(vm_config, indent=2))

    def remove(self, node_name: str) -> None:
        vm_name = self._vm_name(node_name)
        
        # Stop VM if running
        if self.get_state(node_name) == "Running":
            self.stop(node_name)
        
        # Remove VM files
        config_path = self._vm_config_path(node_name)
        if config_path.exists():
            config_path.unlink()
        
        disk_path = self.storage_path / f"{node_name}.qcow2"
        if disk_path.exists():
            disk_path.unlink()

    def list_active(self) -> List[str]:
        # List running QEMU processes for this lab
        try:
            result = run(["pgrep", "-f", f"name {self.lab_prefix}-"], silent=True, check=False)
            if result.returncode == 0:
                pids = result.stdout.strip().split('\n')
                # For each PID, get the command line to extract VM name
                active_vms = []
                for pid in pids:
                    if pid.strip():
                        try:
                            cmd_result = run(["ps", "-p", pid.strip(), "-o", "args="], silent=True, check=False)
                            if cmd_result.returncode == 0:
                                cmd_line = cmd_result.stdout
                                # Extract VM name from command line (this is a simplified approach)
                                # In practice, you'd need more robust parsing
                                for arg in cmd_line.split():
                                    if f"{self.lab_prefix}-" in arg:
                                        vm_name_part = arg.split(f"{self.lab_prefix}-")[-1]
                                        logical_name = self._logical_name(f"{self.lab_prefix}-{vm_name_part}")
                                        if logical_name not in active_vms:
                                            active_vms.append(logical_name)
                        except:
                            continue
                return active_vms
        except:
            pass
        return []

    def exists(self, node_name: str) -> bool:
        config_path = self._vm_config_path(node_name)
        return config_path.exists()

    def start(self, node_name: str) -> None:
        state = self.get_state(node_name)
        if state == "Running":
            # Already running, nothing to do
            return

        vm_name = self._vm_name(node_name)
        config_path = self._vm_config_path(node_name)

        if not config_path.exists():
            raise RuntimeError(f"VM configuration does not exist for {node_name}")

        # Load VM configuration
        config = json.loads(config_path.read_text())

        # Convert memory string to MB for QEMU
        memory_mb = self._convert_memory_to_mb(config["memory"])

        # Build QEMU command
        cmd = [
            "qemu-system-x86_64",
            "-name", vm_name,
            "-m", str(memory_mb),
            "-smp", str(config["cpus"]),
            "-drive", f"file={config['disk']},format=qcow2",
            "-cdrom", config["image"],  # Assuming image is an ISO
            "-boot", "d",  # Boot from CD-ROM
            "-enable-kvm",  # Enable KVM acceleration if available
            "-nographic",  # No GUI
            "-serial", "stdio",  # Connect serial to stdio
            "-pidfile", str(self._get_vm_pid_file(node_name))  # Store PID
        ]

        # Add network configuration
        if config.get("network") == "user":
            cmd.extend(["-netdev", "user,id=net0", "-device", "virtio-net-pci,netdev=net0"])

        # Add additional config if provided
        if config.get("config"):
            # Handle QEMU-specific configurations
            pass

        # Start the VM in background
        subprocess.Popen(cmd)

    def stop(self, node_name: str) -> None:
        state = self.get_state(node_name)
        if state != "Running":
            # Already stopped, nothing to do
            return

        pid_file = self._get_vm_pid_file(node_name)
        if pid_file.exists():
            try:
                with open(pid_file, 'r') as f:
                    pid = f.read().strip()

                if pid and pid.isdigit():
                    run(["kill", pid], check=True)
                    pid_file.unlink()  # Remove PID file after stopping
            except Exception as e:
                # If kill fails, try force kill
                try:
                    with open(pid_file, 'r') as f:
                        pid = f.read().strip()
                    if pid and pid.isdigit():
                        run(["kill", "-9", pid], check=True)
                        pid_file.unlink()
                except:
                    pass  # VM might already be stopped

    def get_state(self, node_name: str) -> Optional[str]:
        pid_file = self._get_vm_pid_file(node_name)
        if not pid_file.exists():
            return "Stopped"
        
        try:
            with open(pid_file, 'r') as f:
                pid = f.read().strip()
            
            if pid and pid.isdigit():
                # Check if process is still running
                run(["kill", "-0", pid], check=True, silent=True)  # kill -0 checks if process exists
                return "Running"
        except subprocess.CalledProcessError:
            # Process doesn't exist, remove stale PID file
            pid_file.unlink()
            return "Stopped"
        except:
            pass
        
        return "Stopped"

    def set_metadata(self, node_name: str, key: str, value: str) -> None:
        config_path = self._vm_config_path(node_name)
        if config_path.exists():
            config = json.loads(config_path.read_text())
            if "metadata" not in config:
                config["metadata"] = {}
            config["metadata"][key] = value
            config_path.write_text(json.dumps(config, indent=2))

    def get_metadata(self, node_name: str, key: str) -> Optional[str]:
        config_path = self._vm_config_path(node_name)
        if config_path.exists():
            config = json.loads(config_path.read_text())
            return config.get("metadata", {}).get(key)
        return None

    def mount_volume(self, node_name: str, source_path: str, target_path: str, readonly: bool = False) -> None:
        # For VMs, volume mounting would typically be done via QEMU drive parameters
        # This is a simplified approach - in practice, you'd need to modify the VM configuration
        config_path = self._vm_config_path(node_name)
        if config_path.exists():
            config = json.loads(config_path.read_text())
            if "volumes" not in config:
                config["volumes"] = []
            
            volume_config = {
                "source": source_path,
                "target": target_path,
                "readonly": readonly
            }
            
            # Check if volume already exists to avoid duplicates
            if volume_config not in config["volumes"]:
                config["volumes"].append(volume_config)
                config_path.write_text(json.dumps(config, indent=2))

    def _convert_memory_to_mb(self, memory_str: str) -> int:
        """Convert memory string (e.g., '1GB', '512MB') to MB integer"""
        memory_str = memory_str.upper()
        if memory_str.endswith('GB'):
            return int(float(memory_str[:-2]) * 1024)
        elif memory_str.endswith('MB'):
            return int(memory_str[:-2])
        elif memory_str.endswith('KB'):
            return int(memory_str[:-2]) // 1024
        else:
            # Assume it's already in MB
            return int(memory_str)