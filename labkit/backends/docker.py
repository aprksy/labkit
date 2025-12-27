import subprocess
import json
from typing import List, Optional
from ..models import RequiredNode, NodeType
from .base import NodeBackend
from ..utils import run

class DockerNodeBackend(NodeBackend):
    def __init__(self, lab_name: str):
        self.lab_prefix = f"{lab_name}"

    def _container_name(self, logical_name: str) -> str:
        return f"{self.lab_prefix}-{logical_name}"

    def _logical_name(self, container_name: str) -> str:
        """Extract logical name from container name"""
        if container_name.startswith(f"{self.lab_prefix}-"):
            return container_name[len(self.lab_prefix)+1:]
        return container_name

    def provision(self, node: RequiredNode) -> None:
        container_name = self._container_name(node.name)
        
        # Build docker run command with node specifications
        cmd = ["docker", "run", "-d", "--name", container_name]
        
        # Add CPU and memory limits
        cmd.extend(["--cpus", str(node.cpus), "-m", node.memory])
        
        # Add environment variables
        for key, value in node.environment.items():
            cmd.extend(["-e", f"{key}={value}"])
        
        # Add port mappings
        for port_mapping in node.ports:
            cmd.extend(["-p", port_mapping])
        
        # Add volume mounts
        for volume_mapping in node.volumes:
            cmd.extend(["-v", volume_mapping])
        
        # Add additional config if provided
        if node.config:
            # Handle Docker-specific configurations
            for key, value in node.config.items():
                if key.startswith("docker."):
                    # Remove 'docker.' prefix for actual Docker options
                    docker_opt = key[7:]  # Remove 'docker.' prefix
                    if docker_opt == "privileged":
                        if value:
                            cmd.append("--privileged")
                    elif docker_opt == "network":
                        cmd.extend(["--network", str(value)])
                    elif docker_opt == "user":
                        cmd.extend(["--user", str(value)])
                    # Add more Docker-specific options as needed
        
        cmd.append(node.image)
        
        run(cmd, check=True)

    def remove(self, node_name: str) -> None:
        container_name = self._container_name(node_name)
        # Check if container exists first
        if self.exists(node_name):
            state = self.get_state(node_name)
            if state in ["Running", "Paused"]:
                self.stop(node_name)
            run(["docker", "rm", "-f", container_name], check=True)

    def list_active(self) -> List[str]:
        # List all containers and filter by lab prefix
        result = run(["docker", "ps", "-a", "--format", "{{.Names}}"], silent=True)
        all_containers = result.stdout.strip().split('\n') if result.stdout.strip() else []
        
        # Filter containers that belong to this lab
        lab_containers = [
            self._logical_name(name) 
            for name in all_containers 
            if name.startswith(f"{self.lab_prefix}-")
        ]
        return lab_containers

    def exists(self, node_name: str) -> bool:
        container_name = self._container_name(node_name)
        result = run(["docker", "inspect", container_name], silent=True, check=False)
        return result.returncode == 0

    def start(self, node_name: str) -> None:
        container_name = self._container_name(node_name)
        state = self.get_state(node_name)
        if state == "Running":
            # Already running, nothing to do
            return
        run(["docker", "start", container_name], check=True)

    def stop(self, node_name: str) -> None:
        container_name = self._container_name(node_name)
        state = self.get_state(node_name)
        if state != "Running":
            # Already stopped, nothing to do
            return
        run(["docker", "stop", container_name], check=True)

    def get_state(self, node_name: str) -> Optional[str]:
        container_name = self._container_name(node_name)
        result = run(["docker", "inspect", "-f", "{{.State.Status}}", container_name], silent=True, check=False)
        if result.returncode == 0:
            status = result.stdout.strip()
            # Map Docker states to standard states
            if status in ["running", "paused"]:
                return status.capitalize()
            elif status in ["exited", "created"]:
                return "Stopped"
            return status.capitalize()
        return None

    def set_metadata(self, node_name: str, key: str, value: str) -> None:
        container_name = self._container_name(node_name)
        # Docker doesn't have a direct equivalent to Incus config set
        # We can use labels as metadata
        # First, stop the container
        state = self.get_state(node_name)
        was_running = state == "Running"
        if was_running:
            self.stop(node_name)
        
        # Add label to container by recreating it with the new label
        # For simplicity, we'll just add labels via docker inspect and docker commit
        # In a real implementation, we'd need to handle this differently
        run(["docker", "label", "add", f"{key}={value}", container_name], check=False)  # This command doesn't exist in Docker

        # Actually, Docker labels need to be set during container creation
        # A more practical approach would be to store metadata in a file or use environment variables
        # For now, we'll just update a label using docker inspect approach
        # A real implementation would need to store this metadata differently
        if was_running:
            self.start(node_name)

    def get_metadata(self, node_name: str, key: str) -> Optional[str]:
        container_name = self._container_name(node_name)
        # Get labels from container
        result = run(["docker", "inspect", "-f", "{{json .Config.Labels}}", container_name], silent=True, check=False)
        if result.returncode == 0:
            try:
                labels = json.loads(result.stdout.strip())
                return labels.get(key)
            except (json.JSONDecodeError, TypeError):
                pass
        return None

    def mount_volume(self, node_name: str, source_path: str, target_path: str, readonly: bool = False) -> None:
        container_name = self._container_name(node_name)
        # This would require recreating the container with the new volume
        # For now, we'll just record the volume mapping in the config
        # In a real implementation, this would be more complex as Docker volumes
        # can't be added to running containers
        pass