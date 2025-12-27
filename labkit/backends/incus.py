import subprocess
import json
from typing import List, Optional
from ..models import RequiredNode, NodeType
from .base import NodeBackend
from ..utils import run

class IncusNodeBackend(NodeBackend):
    def __init__(self, lab_name: str):
        self.lab_prefix = f"{lab_name}"

    def _physical_name(self, logical_name: str) -> str:
        return f"{self.lab_prefix}-{logical_name}"

    def _logical_name(self, physical_name: str) -> str:
        """Extract logical name from physical name"""
        if physical_name.startswith(f"{self.lab_prefix}-"):
            return physical_name[len(self.lab_prefix)+1:]
        return physical_name

    def provision(self, node: RequiredNode) -> None:
        phys_name = self._physical_name(node.name)

        # Check if the 'image' is actually an existing instance (template)
        # If it exists, we should use 'copy' instead of 'init'
        if self._instance_exists(node.image):
            # Use copy for existing instances (templates)
            run(["incus", "copy", node.image, phys_name], check=True)

            # Set resource limits after copying
            self._set_resource_limits(phys_name, node)
        else:
            # Determine if this is a container or VM and create from image
            if node.node_type == NodeType.VM:
                # Create VM from image with disk size specified during init
                cmd = ["incus", "init", node.image, phys_name, "--vm"]
                # Add disk device with size during init
                if node.disk:
                    cmd.extend(["-d", f"root,size={node.disk}"])
                run(cmd, check=True)

                # Set other resource limits after init
                self._set_resource_limits(phys_name, node, include_disk=False)
            else:  # Container
                # Create container from image
                run(["incus", "init", node.image, phys_name], check=True)

                # Set resource limits after init
                self._set_resource_limits(phys_name, node)

        # Set environment variables if any (only for containers)
        if node.node_type != NodeType.VM and node.environment:
            for key, value in node.environment.items():
                run(["incus", "config", "set", phys_name, f"environment.{key}={value}"], check=True)

    def _set_resource_limits(self, phys_name: str, node: RequiredNode, include_disk: bool = True):
        """Helper method to set resource limits"""
        config_args = [
            f"limits.cpu={node.cpus}",
            f"limits.memory={node.memory}"
        ]

        if node.config:
            for key, value in node.config.items():
                config_args.append(f"{key}={value}")

        if config_args:
            config_cmd = ["incus", "config", "set", phys_name] + config_args
            run(config_cmd, check=True)

    def _instance_exists(self, instance_name: str) -> bool:
        """Check if an instance (container/VM) exists"""
        try:
            result = run(["incus", "info", instance_name], silent=True, check=False)
            return result.returncode == 0
        except:
            return False

    def remove(self, node_name: str) -> None:
        phys_name = self._physical_name(node_name)
        # Check if container/VM exists first
        if self.exists(node_name):
            state = self.get_state(node_name)
            if state == "Running":
                self.stop(node_name)
            run(["incus", "delete", phys_name], check=True)

    def list_active(self) -> List[str]:
        result = run(["incus", "list", "--format=json"], silent=True)
        containers = json.loads(result.stdout)
        # Filter containers/VMs that belong to this lab
        lab_nodes = [
            self._logical_name(c["name"])
            for c in containers
            if c["name"].startswith(f"{self.lab_prefix}-")
        ]
        return lab_nodes

    def exists(self, node_name: str) -> bool:
        phys_name = self._physical_name(node_name)
        result = run(["incus", "info", phys_name], silent=True, check=False)
        return result.returncode == 0

    def start(self, node_name: str) -> None:
        phys_name = self._physical_name(node_name)
        state = self.get_state(node_name)
        if state == "Running":
            # Already running, nothing to do
            return
        run(["incus", "start", phys_name], check=True)

    def stop(self, node_name: str) -> None:
        phys_name = self._physical_name(node_name)
        state = self.get_state(node_name)
        if state != "Running":
            # Already stopped, nothing to do
            return
        run(["incus", "stop", phys_name], check=True)

    def get_state(self, node_name: str) -> Optional[str]:
        phys_name = self._physical_name(node_name)
        result = run(["incus", "list", phys_name, "--format=json"], silent=True, check=False)
        if result.returncode != 0:
            return None
        try:
            data = json.loads(result.stdout)
            for c in data:
                if c["name"] == phys_name:
                    return c["status"]
            return None
        except Exception:
            return None

    def set_metadata(self, node_name: str, key: str, value: str) -> None:
        phys_name = self._physical_name(node_name)
        run(["incus", "config", "set", phys_name, f"user.{key}={value}"], check=True)

    def get_metadata(self, node_name: str, key: str) -> Optional[str]:
        phys_name = self._physical_name(node_name)
        result = run(["incus", "config", "get", phys_name, f"user.{key}"], silent=True, check=False)
        if result.returncode == 0:
            return result.stdout.strip()
        return None

    def mount_volume(self, node_name: str, source_path: str, target_path: str, readonly: bool = False) -> None:
        phys_name = self._physical_name(node_name)
        readonly_flag = "readonly=true" if readonly else "readonly=false"
        run([
            "incus", "config", "device", "add", phys_name,
            f"mount-{len(source_path)}", "disk",
            f"path={target_path}", f"source={source_path}", readonly_flag
        ], check=True)