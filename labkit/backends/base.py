from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from ..models import RequiredNode, NodeType

class NodeBackend(ABC):
    """
    Abstract interface for node lifecycle management.
    Concrete implementations handle backend-specific details (Incus, Docker, QEMU, etc.).
    """

    @abstractmethod
    def provision(self, node: RequiredNode) -> None:
        """
        Create or update a node to match the RequiredNode spec.
        Idempotent: safe to call multiple times.
        """
        pass

    @abstractmethod
    def remove(self, node_name: str) -> None:
        """
        Remove the node by its logical name.
        Should raise if node does not exist (unless idempotent removal is desired).
        """
        pass

    @abstractmethod
    def list_active(self) -> List[str]:
        """
        Return list of logical node names currently active in this backend.
        Used by `labkit list`.
        """
        pass

    @abstractmethod
    def exists(self, node_name: str) -> bool:
        """Check if a node with the given logical name exists."""
        pass

    @abstractmethod
    def start(self, node_name: str) -> None:
        """Start a node."""
        pass

    @abstractmethod
    def stop(self, node_name: str) -> None:
        """Stop a node."""
        pass

    @abstractmethod
    def get_state(self, node_name: str) -> Optional[str]:
        """
        Get the current state of a node.
        Returns: 'Running', 'Stopped', 'Paused', or None if not found.
        """
        pass

    @abstractmethod
    def set_metadata(self, node_name: str, key: str, value: str) -> None:
        """Set metadata on a node."""
        pass

    @abstractmethod
    def get_metadata(self, node_name: str, key: str) -> Optional[str]:
        """Get metadata from a node."""
        pass

    @abstractmethod
    def mount_volume(self, node_name: str, source_path: str, target_path: str, readonly: bool = False) -> None:
        """Mount a volume to a node."""
        pass