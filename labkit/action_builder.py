"""
action_builder.py: Module for building and planning lab actions
"""
import json
import subprocess
from pathlib import Path
from typing import List, Dict, Any, Callable, Optional
from .models import NodeType, RequiredNode
from .backends.base import NodeBackend
from .utils import run, info, success, error, warning


class ActionBuilder:
    """
    ActionBuilder: Class responsible for building action plans for lab operations
    """

    def __init__(self, backend: NodeBackend, config: Dict[str, Any], root: Path):
        self.backend = backend
        self.config = config
        self.root = root
        self.nodes_dir = root / "nodes"
        self.shared_dir = root / "shared"

    def build_add_node_actions(self, node: RequiredNode, dry_run: bool = False) -> List[Dict[str, Any]]:
        """
        Build actions for adding a node
        :param node: Node specification
        :param dry_run: Whether this is a dry run
        :return: List of action dictionaries
        """
        actions = []

        # 1. Create node via backend
        actions.append({
            "desc": f"Create {node.node_type.value} '{node.name}' from '{node.image}'",
            "func": self.backend.provision,
            "args": (node,),
            "kwargs": {}
        })

        # 2. Create node directory
        node_dir = self.nodes_dir / node.name
        actions.append({
            "desc": f"Create directory {node_dir}",
            "func": lambda path: path.mkdir(exist_ok=True),
            "args": (node_dir,)
        })

        # 3. Write manifest
        def write_manifest():
            manifest_content = f"""name: {node.name}
node_type: {node.node_type.value}
image: {node.image}
cpus: {node.cpus}
memory: {node.memory}
disk: {node.disk}
purpose: >-
  Replace with purpose
role: unknown
tags: []
environment: development
owner: {self.config.get('user', 'unknown')}
lifecycle: experimental
created_via: labkit node add
dependencies: []
notes: |
  Add usage notes, gotchas, maintenance tips here.
"""
            (node_dir / "manifest.yaml").write_text(manifest_content)

        actions.append({
            "desc": f"Generate {node_dir}/manifest.yaml",
            "func": write_manifest
        })

        # 4. Write README
        def write_readme():
            (node_dir / "README.md").write_text(
                f"# {node.name}\n\n> Update this with purpose and usage\n")

        actions.append({
            "desc": f"Generate {node_dir}/README.md",
            "func": write_readme
        })

        # 5. Mount node directory
        actions.append({
            "desc": f"Mount {node_dir} → {node.name}:/lab/node",
            "func": self.backend.mount_volume,
            "args": (node.name, str(node_dir), "/lab/node")
        })

        # 6. Mount shared storage if enabled
        if self.config.get("shared_storage", {}).get("enabled", True):
            shared_mp = self.config.get("shared_storage", {}).get("mount_point", "/lab/shared")
            actions.append({
                "desc": f"Mount {self.shared_dir} → {node.name}:{shared_mp}",
                "func": self.backend.mount_volume,
                "args": (node.name, str(self.shared_dir), shared_mp)
            })

        # 7. Set labels
        actions.append({
            "desc": f"Set labels on {node.name}",
            "func": self.backend.set_metadata,
            "args": (node.name, "lab", self.config["name"])
        })

        actions.append({
            "desc": f"Set managed-by label on {node.name}",
            "func": self.backend.set_metadata,
            "args": (node.name, "managed-by", "labkit")
        })

        # 8. Git commit
        def git_commit():
            import subprocess
            import os
            subprocess.run(["git", "add", "."], cwd=self.root, check=False)
            env = os.environ.copy()
            env.setdefault("GIT_AUTHOR_NAME", "labkit")
            env.setdefault("GIT_COMMITTER_NAME", "labkit")
            env.setdefault("GIT_AUTHOR_EMAIL", "labkit@localhost")
            env.setdefault("GIT_COMMITTER_EMAIL", "labkit@localhost")
            subprocess.run([
                "git", "commit", "-m", f"labkit: added node {node.name}"
            ], cwd=self.root, env=env, check=False)  # ignore no-changes

        actions.append({
            "desc": "Commit node metadata to Git",
            "func": git_commit
        })

        return actions

    def build_remove_node_actions(self, node_name: str, force: bool = False, dry_run: bool = False) -> List[Dict[str, Any]]:
        """
        Build actions for removing a node
        :param node_name: Name of node to remove
        :param force: Whether to force removal
        :param dry_run: Whether this is a dry run
        :return: List of action dictionaries
        """
        actions = []

        # 1. Check if node exists
        if not self.backend.exists(node_name):
            warning(f"Node '{node_name}' not found")
            return actions  # Return empty actions if node doesn't exist

        # 2. Get node state
        state = self.backend.get_state(node_name)

        # 3. Stop node if running and not forced
        if state == "Running" and not force:
            warning(f"'{node_name}' is running. Use --force to stop and delete.")
            return actions
        elif state == "Running":
            actions.append({
                "desc": f"Stop node: {node_name}",
                "func": self.backend.stop,
                "args": (node_name,),
                "kwargs": {}
            })

        # 4. Remove node via backend
        actions.append({
            "desc": f"Remove node: {node_name}",
            "func": self.backend.remove,
            "args": (node_name,),
            "kwargs": {}
        })

        # 5. Git commit
        def git_commit():
            import subprocess
            import os
            subprocess.run(["git", "add", "."], cwd=self.root, check=False)
            env = os.environ.copy()
            env.setdefault("GIT_AUTHOR_NAME", "labkit")
            env.setdefault("GIT_COMMITTER_NAME", "labkit")
            env.setdefault("GIT_AUTHOR_EMAIL", "labkit@localhost")
            subprocess.run([
                "git", "commit", "-m", f"labkit: removed node {node_name}"
            ], cwd=self.root, env=env, check=False)  # ignore no-changes

        actions.append({
            "desc": "Commit removal to Git",
            "func": git_commit
        })

        return actions

    def build_up_actions(self, only: Optional[List[str]] = None, include_deps: bool = True, dry_run: bool = False) -> List[Dict[str, Any]]:
        """
        Build actions for bringing the lab up
        :param only: List of specific nodes to start (None for all)
        :param include_deps: Whether to include required nodes
        :param dry_run: Whether this is a dry run
        :return: List of action dictionaries
        """
        import subprocess
        import json
        from .utils import warning, info, run

        actions = []

        # Get current node states via backend
        local_running_names = set(self.backend.list_active())

        # For dependencies, we still need to check with the original system (Incus)
        # In a full implementation, dependencies would also use the backend abstraction
        if self.config.get("backend", "incus") == "incus":
            result = run(["incus", "list", "--format=json"], silent=True)
            containers = json.loads(result.stdout)
            running_names = {c["name"] for c in containers if c["status"] == "Running"}
        else:
            # For other backends, we might need different logic
            running_names = local_running_names

        # Determine which local nodes to start
        local_node_dirs = [d.name for d in self.nodes_dir.iterdir() if d.is_dir()]
        local_to_start = []

        if only:
            target_nodes = [n.strip() for n in only.split(",") if n.strip()]
            info(f"Target nodes: {', '.join(target_nodes)}")
            for name in target_nodes:
                if name not in local_node_dirs:
                    warning(f"Node '{name}' not found in nodes/ — skipping")
                else:
                    # local_running_names contains logical names from backend
                    scoped_name = f"{self.config['name']}-{name}"
                    if scoped_name not in local_running_names:
                        local_to_start.append(name)
        else:
            # Start all local nodes that aren't running
            for node_name in local_node_dirs:
                # local_running_names contains logical names from backend
                scoped_name = f"{self.config['name']}-{node_name}"
                if scoped_name not in local_running_names:
                    local_to_start.append(node_name)

        # Determine required nodes to start (for now, only support Incus for dependencies)
        required_to_start = []
        if include_deps and self.config.get("backend", "incus") == "incus":
            required_nodes = self.config.get("requires_nodes", [])
            required_to_start = [n for n in required_nodes if n not in running_names]

        # Build actions
        # Start required nodes first (only for Incus for now)
        for name in required_to_start:
            actions.append({
                "desc": f"Start required node: {name}",
                "func": subprocess.run,
                "args": (["incus", "start", name],),
                "kwargs": {"check": True}
            })

        # Start local nodes via backend
        for name in local_to_start:
            actions.append({
                "desc": f"Start local node: {name}",
                "func": self.backend.start,
                "args": (name,),
                "kwargs": {}
            })

        # Log event
        def log_up():
            from datetime import datetime
            import getpass
            log_dir = self.root / "logs"
            log_dir.mkdir(exist_ok=True)
            timestamp = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
            log_file = log_dir / f"{timestamp}-up.txt"

            data = {
                "action": "up",
                "user": getpass.getuser(),
                "timestamp": timestamp,
                "lab": self.config["name"],
                "nodes_started": local_to_start,
                "requires_started": required_to_start,
                "filtered": only
            }

            lines = [f"{k.upper()}: {v}" for k, v in data.items()]
            log_file.write_text("\n".join(lines) + "\n")

        if actions:
            actions.append({
                "desc": "Log up event",
                "func": log_up
            })

        return actions

    def build_down_actions(self, only: Optional[List[str]] = None, suspend_required: bool = False, force_stop_all: bool = False, dry_run: bool = False) -> List[Dict[str, Any]]:
        """
        Build actions for bringing the lab down
        :param only: List of specific nodes to stop (None for all)
        :param suspend_required: Whether to suspend required nodes
        :param force_stop_all: Whether to force stop all nodes
        :param dry_run: Whether this is a dry run
        :return: List of action dictionaries
        """
        import subprocess
        import json
        from .utils import warning, info, error, run

        actions = []

        # Get current node states via backend
        local_running_names = set(self.backend.list_active())

        # For dependencies, we still need to check with the original system (Incus)
        # In a full implementation, dependencies would also use the backend abstraction
        if self.config.get("backend", "incus") == "incus":
            result = run(["incus", "list", "--format=json"], silent=True)
            containers = json.loads(result.stdout)
            running_names = {c["name"] for c in containers if c["status"] == "Running"}
        else:
            # For other backends, we might need different logic
            running_names = local_running_names

        # Determine which local nodes to stop
        local_node_dirs = [d.name for d in self.nodes_dir.iterdir() if d.is_dir()]
        local_to_stop = []

        if only and (force_stop_all or suspend_required):
            error("Cannot use '--force-stop-all' and/or '--suspend-required' with '--only'")
            return []  # Return empty actions for error condition

        # Process --only flag
        if only:
            target_nodes = [n.strip() for n in only.split(",") if n.strip()]
            info(f"Target nodes: {', '.join(target_nodes)}")
            for name in target_nodes:
                if name not in local_node_dirs:
                    warning(f"Node '{name}' not found in nodes/ — skipping")
                else:
                    # Compare logical names from nodes/ directory with logical names from backend
                    if name in local_running_names:
                        local_to_stop.append(name)
                    else:
                        info(f"Node '{name}' already stopped")
        else:
            # Stop all running local nodes
            local_to_stop = [n for n in local_node_dirs if n in local_running_names]

        # Determine required nodes to suspend (for now, only support Incus for dependencies)
        required_to_suspend = []
        if suspend_required and self.config.get("backend", "incus") == "incus":
            required_nodes = self.config.get("requires_nodes", [])
            for name in required_nodes:
                if name not in running_names:
                    continue  # already stopped
                if not force_stop_all:
                    # Check if pinned (only for Incus for now)
                    pin_result = run(
                        ["incus", "config", "get", name, "user.pinned"],
                        silent=True, check=False
                    )
                    if pin_result.returncode == 0 and pin_result.stdout.strip() == "true":
                        info(f"Skipping {name}: user.pinned=true")
                        continue
                    # Future: refcount check via user.required_by
                required_to_suspend.append(name)

        # Build actions
        # Stop local nodes via backend
        for name in local_to_stop:
            actions.append({
                "desc": f"Stop local node: {name}",
                "func": self.backend.stop,
                "args": (name,),
                "kwargs": {}
            })

        # Suspend required nodes (only for Incus for now)
        for name in required_to_suspend:
            actions.append({
                "desc": f"Suspend required node: {name}",
                "func": subprocess.run,
                "args": (["incus", "stop", name],),
                "kwargs": {"check": True}
            })

        # Log event
        def log_down():
            from datetime import datetime
            import getpass
            log_dir = self.root / "logs"
            log_dir.mkdir(exist_ok=True)
            timestamp = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
            log_file = log_dir / f"{timestamp}-down.txt"

            data = {
                "action": "down",
                "user": getpass.getuser(),
                "timestamp": timestamp,
                "lab": self.config["name"],
                "nodes_stopped": local_to_stop,
                "requires_suspended": required_to_suspend,
                "filtered": only
            }

            lines = [f"{k.upper()}: {v}" for k, v in data.items()]
            log_file.write_text("\n".join(lines) + "\n")

        if actions:
            actions.append({
                "desc": "Log down event",
                "func": log_down
            })

        return actions