"""
fs_writer.py: Infrastructure for secure filesystem operations by plugins
"""
import abc
import os
import stat
from pathlib import Path
from typing import Dict, Any, Union, Optional
import logging
import tempfile
import shutil

from .interfaces import UtilityPlugin


class SecureFSWriter(abc.ABC):
    """
    SecureFSWriter: Base class for secure filesystem operations
    Provides safe methods for plugins to write to the filesystem
    """

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = logging.getLogger("plugin.fs_writer")
        self.allowed_paths = config.get("allowed_paths", [])
        self.max_file_size = config.get("max_file_size", 10 * 1024 * 1024)  # 10MB default

    def _validate_path(self, path: Union[str, Path]) -> bool:
        """
        Validate that a path is within allowed directories
        :param path: Path to validate
        :return: True if path is valid
        """
        path = Path(path).resolve()

        for allowed_path in self.allowed_paths:
            allowed_path = Path(allowed_path).resolve()
            try:
                path.relative_to(allowed_path)
                return True
            except ValueError:
                continue

        return False

    def write_file(self, path: Union[str, Path], content: Union[str, bytes], mode: int = 0o644) -> bool:
        """
        Securely write content to a file
        :param path: Path to write to
        :param content: Content to write
        :param mode: File permissions (default 0o644)
        :return: True if write succeeds
        """
        path = Path(path)
        
        # Validate path
        if not self._validate_path(path):
            self.logger.error(f"Path not in allowed paths: {path}")
            return False

        # Check file size for string content
        if isinstance(content, str) and len(content.encode()) > self.max_file_size:
            self.logger.error(f"Content exceeds max size ({self.max_file_size} bytes): {path}")
            return False
        elif isinstance(content, bytes) and len(content) > self.max_file_size:
            self.logger.error(f"Content exceeds max size ({self.max_file_size} bytes): {path}")
            return False

        try:
            # Create parent directories if they don't exist
            path.parent.mkdir(parents=True, exist_ok=True)

            # Use atomic write with tempfile
            with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as tmp_file:
                if isinstance(content, str):
                    tmp_file.write(content.encode())
                else:
                    tmp_file.write(content)
                tmp_path = Path(tmp_file.name)

            # Set permissions before moving
            os.chmod(tmp_path, mode)
            
            # Atomic move
            shutil.move(str(tmp_path), str(path))
            
            self.logger.info(f"Successfully wrote file: {path}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to write file {path}: {e}")
            # Clean up temp file if it exists
            try:
                tmp_path.unlink(missing_ok=True)
            except:
                pass
            return False

    def append_file(self, path: Union[str, Path], content: Union[str, bytes]) -> bool:
        """
        Securely append content to a file
        :param path: Path to append to
        :param content: Content to append
        :return: True if append succeeds
        """
        path = Path(path)
        
        # Validate path
        if not self._validate_path(path):
            self.logger.error(f"Path not in allowed paths: {path}")
            return False

        try:
            # Check if file exists and its size
            if path.exists():
                current_size = path.stat().st_size
                content_size = len(content.encode() if isinstance(content, str) else content)
                if current_size + content_size > self.max_file_size:
                    self.logger.error(f"Append would exceed max size ({self.max_file_size} bytes): {path}")
                    return False

            # Append to file
            with path.open("a" if isinstance(content, str) else "ab") as f:
                f.write(content)

            self.logger.info(f"Successfully appended to file: {path}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to append to file {path}: {e}")
            return False

    def create_directory(self, path: Union[str, Path], mode: int = 0o755) -> bool:
        """
        Securely create a directory
        :param path: Path to create
        :param mode: Directory permissions (default 0o755)
        :return: True if creation succeeds
        """
        path = Path(path)
        
        # Validate path
        if not self._validate_path(path):
            self.logger.error(f"Path not in allowed paths: {path}")
            return False

        try:
            path.mkdir(parents=True, mode=mode, exist_ok=True)
            self.logger.info(f"Successfully created directory: {path}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to create directory {path}: {e}")
            return False

    def delete_file(self, path: Union[str, Path]) -> bool:
        """
        Securely delete a file
        :param path: Path to delete
        :return: True if deletion succeeds
        """
        path = Path(path)
        
        # Validate path
        if not self._validate_path(path):
            self.logger.error(f"Path not in allowed paths: {path}")
            return False

        try:
            if path.exists():
                path.unlink()
                self.logger.info(f"Successfully deleted file: {path}")
            else:
                self.logger.warning(f"File does not exist: {path}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to delete file {path}: {e}")
            return False

    def get_allowed_paths(self) -> list:
        """
        Get list of allowed paths
        :return: List of allowed paths
        """
        return self.allowed_paths.copy()

    def add_allowed_path(self, path: Union[str, Path]) -> bool:
        """
        Add a path to the allowed paths list
        :param path: Path to add
        :return: True if addition succeeds
        """
        path = str(Path(path).resolve())
        if path not in self.allowed_paths:
            self.allowed_paths.append(path)
            self.logger.info(f"Added allowed path: {path}")
            return True
        return False


class SecureSSHConfigWriter(SecureFSWriter):
    """
    SecureSSHConfigWriter: Specialized writer for SSH configuration files
    """

    def __init__(self, config: Dict[str, Any]):
        # Add SSH config directory to allowed paths
        ssh_config_dir = config.get("ssh_config_dir", str(Path.home() / ".ssh"))
        if ssh_config_dir not in config.get("allowed_paths", []):
            if "allowed_paths" not in config:
                config["allowed_paths"] = []
            config["allowed_paths"].append(ssh_config_dir)

        super().__init__(config)
        self.ssh_config_path = Path(config.get("ssh_config_path", str(ssh_config_dir) + "/labkit_config"))

    def write_ssh_config_entry(self, host: str, hostname: str, user: str, identity_file: str = None, 
                              port: int = 22, options: Dict[str, str] = None) -> bool:
        """
        Write a single SSH config entry
        :param host: Host nickname
        :param hostname: Actual hostname/IP
        :param user: SSH user
        :param identity_file: Path to identity file
        :param port: SSH port
        :param options: Additional SSH options
        :return: True if write succeeds
        """
        # Validate host name (basic security check)
        if not host.replace('-', '').replace('_', '').replace('.', '').isalnum():
            self.logger.error(f"Invalid host name: {host}")
            return False

        # Build SSH config entry
        entry_parts = [f"Host {host}", f"  HostName {hostname}", f"  User {user}", f"  Port {port}"]
        
        if identity_file:
            entry_parts.append(f"  IdentityFile {identity_file}")
        
        if options:
            for key, value in options.items():
                entry_parts.append(f"  {key} {value}")
        
        entry = "\n".join(entry_parts) + "\n"
        
        # Read existing config to preserve other entries
        existing_content = ""
        if self.ssh_config_path.exists():
            try:
                existing_content = self.ssh_config_path.read_text()
            except Exception as e:
                self.logger.warning(f"Could not read existing SSH config: {e}")
        
        # Check if host entry already exists and replace it
        lines = existing_content.split('\n')
        new_lines = []
        in_target_host_block = False
        host_added = False
        
        i = 0
        while i < len(lines):
            line = lines[i]
            if line.strip().startswith(f"Host {host}") and not in_target_host_block:
                # Skip the entire host block (we'll add the new one at the end)
                in_target_host_block = True
                i += 1
                continue
            elif in_target_host_block and line.strip().startswith('Host ') and not line.strip().startswith(f"Host {host}"):
                # Found next host block, so we're done skipping
                in_target_host_block = False
                new_lines.append(line)
            elif not in_target_host_block:
                new_lines.append(line)
            i += 1
        
        # Add the new entry
        if new_lines and new_lines[-1].strip() != "":
            new_lines.append("")  # Add blank line before new entry
        new_lines.append(entry.rstrip())  # Remove trailing newline since entry already has it
        
        # Write the updated config
        new_content = "\n".join(new_lines)
        return self.write_file(self.ssh_config_path, new_content, mode=0o600)