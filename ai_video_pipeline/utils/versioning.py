"""
Artifact hashing and versioning utilities.

This module provides utilities for hashing and versioning artifacts
to support rollback capabilities in the AI Video Pipeline.
"""

import os
import json
import hashlib
import logging
import shutil
from pathlib import Path
from typing import Dict, Any, List, Optional, Union
from datetime import datetime

logger = logging.getLogger(__name__)


def compute_file_hash(file_path: Union[str, Path]) -> str:
    """
    Compute the SHA-256 hash of a file.
    
    Args:
        file_path: Path to the file
    
    Returns:
        str: Hexadecimal hash string
    
    Raises:
        FileNotFoundError: If the file does not exist
    """
    file_path = Path(file_path)
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")
    
    # Use a buffer to handle large files efficiently
    hash_obj = hashlib.sha256()
    with open(file_path, 'rb') as f:
        # Read and update hash in chunks of 4K
        for byte_block in iter(lambda: f.read(4096), b""):
            hash_obj.update(byte_block)
    
    return hash_obj.hexdigest()


def compute_string_hash(content: str) -> str:
    """
    Compute the SHA-256 hash of a string.
    
    Args:
        content: String content to hash
    
    Returns:
        str: Hexadecimal hash string
    """
    hash_obj = hashlib.sha256()
    hash_obj.update(content.encode('utf-8'))
    return hash_obj.hexdigest()


def compute_json_hash(data: Dict[str, Any]) -> str:
    """
    Compute the SHA-256 hash of a JSON-serializable object.
    
    Args:
        data: JSON-serializable object
    
    Returns:
        str: Hexadecimal hash string
    """
    # Sort keys for consistent hashing
    json_str = json.dumps(data, sort_keys=True)
    return compute_string_hash(json_str)


class ArtifactVersion:
    """
    Class representing a versioned artifact.
    
    This class stores metadata about a versioned artifact,
    including its path, hash, timestamp, and parent version.
    """
    
    def __init__(
        self,
        artifact_path: Union[str, Path],
        artifact_type: str,
        job_id: str,
        parent_version_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize an ArtifactVersion.
        
        Args:
            artifact_path: Path to the artifact
            artifact_type: Type of artifact (e.g., 'image', 'audio', 'video')
            job_id: ID of the job that created the artifact
            parent_version_id: ID of the parent version (for tracking lineage)
            metadata: Additional metadata about the artifact
        """
        self.path = Path(artifact_path)
        self.type = artifact_type
        self.job_id = job_id
        self.parent_version_id = parent_version_id
        self.metadata = metadata or {}
        
        # Generate timestamp
        self.timestamp = datetime.now().isoformat()
        
        # Compute hash if file exists
        if self.path.exists():
            self.hash = compute_file_hash(self.path)
        else:
            self.hash = None
            logger.warning(f"Artifact file not found: {self.path}")
        
        # Generate version ID from hash and timestamp
        hash_prefix = self.hash[:8] if self.hash else "nohash"
        timestamp_str = datetime.now().strftime("%Y%m%d%H%M%S")
        self.version_id = f"{hash_prefix}-{timestamp_str}"
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the artifact version to a dictionary.
        
        Returns:
            Dict[str, Any]: Dictionary representation
        """
        return {
            "version_id": self.version_id,
            "path": str(self.path),
            "type": self.type,
            "hash": self.hash,
            "timestamp": self.timestamp,
            "job_id": self.job_id,
            "parent_version_id": self.parent_version_id,
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ArtifactVersion':
        """
        Create an ArtifactVersion from a dictionary.
        
        Args:
            data: Dictionary representation
        
        Returns:
            ArtifactVersion: New instance
        """
        instance = cls(
            artifact_path=data["path"],
            artifact_type=data["type"],
            job_id=data["job_id"],
            parent_version_id=data.get("parent_version_id"),
            metadata=data.get("metadata", {})
        )
        instance.version_id = data["version_id"]
        instance.hash = data["hash"]
        instance.timestamp = data["timestamp"]
        return instance


class ArtifactVersionRegistry:
    """
    Registry for tracking and managing artifact versions.
    
    This class provides methods for registering, retrieving,
    and rolling back artifact versions.
    """
    
    def __init__(self, registry_dir: Union[str, Path]):
        """
        Initialize an ArtifactVersionRegistry.
        
        Args:
            registry_dir: Directory to store the registry
        """
        self.registry_dir = Path(registry_dir)
        self.registry_file = self.registry_dir / "artifact_registry.json"
        self.versions_dir = self.registry_dir / "versions"
        
        # Create directories if they don't exist
        self.registry_dir.mkdir(parents=True, exist_ok=True)
        self.versions_dir.mkdir(parents=True, exist_ok=True)
        
        # Load existing registry or create a new one
        self.registry = self._load_registry()
    
    def _load_registry(self) -> Dict[str, List[Dict[str, Any]]]:
        """
        Load the registry from disk.
        
        Returns:
            Dict[str, List[Dict[str, Any]]]: Registry data
        """
        if self.registry_file.exists():
            try:
                with open(self.registry_file, 'r') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                logger.error(f"Error loading registry: {e}")
                return {}
        else:
            return {}
    
    def _save_registry(self):
        """Save the registry to disk."""
        try:
            with open(self.registry_file, 'w') as f:
                json.dump(self.registry, f, indent=2)
        except IOError as e:
            logger.error(f"Error saving registry: {e}")
    
    def register_artifact(
        self,
        artifact_path: Union[str, Path],
        artifact_type: str,
        job_id: str,
        parent_version_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        store_copy: bool = True
    ) -> ArtifactVersion:
        """
        Register an artifact with the registry.
        
        Args:
            artifact_path: Path to the artifact
            artifact_type: Type of artifact
            job_id: ID of the job that created the artifact
            parent_version_id: ID of the parent version
            metadata: Additional metadata
            store_copy: Whether to store a copy of the artifact
        
        Returns:
            ArtifactVersion: The registered version
        """
        # Create artifact version
        version = ArtifactVersion(
            artifact_path=artifact_path,
            artifact_type=artifact_type,
            job_id=job_id,
            parent_version_id=parent_version_id,
            metadata=metadata
        )
        
        # Store a copy of the artifact if requested
        if store_copy and version.path.exists():
            version_path = self.versions_dir / f"{version.version_id}{version.path.suffix}"
            try:
                shutil.copy2(version.path, version_path)
                logger.info(f"Stored copy of artifact at {version_path}")
            except IOError as e:
                logger.error(f"Error storing artifact copy: {e}")
        
        # Add to registry
        artifact_id = str(version.path)
        if artifact_id not in self.registry:
            self.registry[artifact_id] = []
        
        self.registry[artifact_id].append(version.to_dict())
        self._save_registry()
        
        logger.info(f"Registered artifact {artifact_id} with version {version.version_id}")
        return version
    
    def get_artifact_versions(
        self,
        artifact_path: Union[str, Path]
    ) -> List[ArtifactVersion]:
        """
        Get all versions of an artifact.
        
        Args:
            artifact_path: Path to the artifact
        
        Returns:
            List[ArtifactVersion]: List of versions
        """
        artifact_id = str(Path(artifact_path))
        if artifact_id not in self.registry:
            return []
        
        return [
            ArtifactVersion.from_dict(version_data)
            for version_data in self.registry[artifact_id]
        ]
    
    def get_artifact_version(
        self,
        artifact_path: Union[str, Path],
        version_id: str
    ) -> Optional[ArtifactVersion]:
        """
        Get a specific version of an artifact.
        
        Args:
            artifact_path: Path to the artifact
            version_id: Version ID
        
        Returns:
            Optional[ArtifactVersion]: The version, or None if not found
        """
        versions = self.get_artifact_versions(artifact_path)
        for version in versions:
            if version.version_id == version_id:
                return version
        return None
    
    def rollback_artifact(
        self,
        artifact_path: Union[str, Path],
        version_id: str
    ) -> bool:
        """
        Roll back an artifact to a specific version.
        
        Args:
            artifact_path: Path to the artifact
            version_id: Version ID to roll back to
        
        Returns:
            bool: True if successful, False otherwise
        """
        artifact_path = Path(artifact_path)
        version = self.get_artifact_version(artifact_path, version_id)
        if not version:
            logger.error(f"Version {version_id} not found for {artifact_path}")
            return False
        
        # Check if version file exists
        version_path = self.versions_dir / f"{version.version_id}{artifact_path.suffix}"
        if not version_path.exists():
            logger.error(f"Version file not found: {version_path}")
            return False
        
        try:
            # Create a backup of the current file
            if artifact_path.exists():
                backup_version = self.register_artifact(
                    artifact_path=artifact_path,
                    artifact_type=version.type,
                    job_id=version.job_id,
                    metadata={"rollback_source": True}
                )
                logger.info(f"Created backup version {backup_version.version_id}")
            
            # Copy the version file to the original location
            artifact_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(version_path, artifact_path)
            logger.info(f"Rolled back {artifact_path} to version {version_id}")
            
            return True
            
        except IOError as e:
            logger.error(f"Error rolling back artifact: {e}")
            return False
    
    def get_artifact_lineage(
        self,
        artifact_path: Union[str, Path]
    ) -> List[Dict[str, Any]]:
        """
        Get the lineage of an artifact.
        
        Args:
            artifact_path: Path to the artifact
        
        Returns:
            List[Dict[str, Any]]: Lineage information
        """
        versions = self.get_artifact_versions(artifact_path)
        if not versions:
            return []
        
        # Build a map of version_id to version
        version_map = {v.version_id: v for v in versions}
        
        # Find the latest version
        latest_version = max(versions, key=lambda v: v.timestamp)
        
        # Build lineage by following parent links
        lineage = []
        current = latest_version
        
        while current:
            lineage.append(current.to_dict())
            if current.parent_version_id and current.parent_version_id in version_map:
                current = version_map[current.parent_version_id]
            else:
                current = None
        
        return lineage
