from dataclasses import dataclass
from typing import Optional, Dict, Any, List
from enum import Enum

class NodeType(Enum):
    CONTAINER = "container"
    VM = "vm"
    OCI = "oci"

@dataclass(frozen=True)
class RequiredNode:
    """
    Immutable declaration of a desired node.
    Backend-agnostic; used as input to NodeBackend.provision().
    """
    name: str                          # Logical name (e.g., "db", "web")
    node_type: NodeType                # Type of node (container, vm, oci)
    image: str                         # Base image or template
    cpus: int = 1
    memory: str = "512MB"              # e.g., "1GB", "256MB"
    disk: str = "4GiB"
    environment: Dict[str, str] = None  # Optional env vars
    config: Dict[str, Any] = None       # Backend-specific config passthrough
    ports: List[str] = None             # Port mappings (host:container)
    volumes: List[str] = None           # Volume mounts

    def __post_init__(self):
        # Enforce basic validation
        if not self.name or not self.image:
            raise ValueError("Node name and image are required.")
        if self.cpus < 1:
            raise ValueError("CPU count must be >= 1.")
        if self.environment is None:
            object.__setattr__(self, 'environment', {})
        if self.config is None:
            object.__setattr__(self, 'config', {})
        if self.ports is None:
            object.__setattr__(self, 'ports', [])
        if self.volumes is None:
            object.__setattr__(self, 'volumes', [])