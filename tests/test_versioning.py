"""
Tests for the artifact versioning utilities.

This module contains tests for the artifact versioning utilities in the AI Video Pipeline.
"""

import json
import os
import shutil
import tempfile
from pathlib import Path
from unittest.mock import patch, mock_open

import pytest

from ai_video_pipeline.utils.versioning import (
    compute_file_hash,
    compute_string_hash,
    compute_json_hash,
    ArtifactVersion,
    ArtifactVersionRegistry
)


class TestHashingFunctions:
    """Tests for the hashing utility functions."""
    
    def test_compute_file_hash(self, tmp_path):
        """Test computing a file hash."""
        # Create a test file
        test_file = tmp_path / "test_file.txt"
        test_content = "Test content for hashing"
        test_file.write_text(test_content)
        
        # Compute the hash
        file_hash = compute_file_hash(test_file)
        
        # Verify it's a valid SHA-256 hash (64 hex characters)
        assert len(file_hash) == 64
        assert all(c in "0123456789abcdef" for c in file_hash)
        
        # Verify the hash is consistent
        assert compute_file_hash(test_file) == file_hash
        
        # Verify the hash changes when content changes
        test_file.write_text(test_content + " modified")
        assert compute_file_hash(test_file) != file_hash
    
    def test_compute_file_hash_nonexistent_file(self):
        """Test that compute_file_hash raises FileNotFoundError for nonexistent files."""
        with pytest.raises(FileNotFoundError):
            compute_file_hash("nonexistent_file.txt")
    
    def test_compute_string_hash(self):
        """Test computing a string hash."""
        # Compute the hash of a string
        test_string = "Test string for hashing"
        string_hash = compute_string_hash(test_string)
        
        # Verify it's a valid SHA-256 hash
        assert len(string_hash) == 64
        assert all(c in "0123456789abcdef" for c in string_hash)
        
        # Verify the hash is consistent
        assert compute_string_hash(test_string) == string_hash
        
        # Verify the hash changes when the string changes
        assert compute_string_hash(test_string + " modified") != string_hash
    
    def test_compute_json_hash(self):
        """Test computing a JSON hash."""
        # Compute the hash of a dictionary
        test_dict = {"key1": "value1", "key2": 2, "key3": [1, 2, 3]}
        json_hash = compute_json_hash(test_dict)
        
        # Verify it's a valid SHA-256 hash
        assert len(json_hash) == 64
        assert all(c in "0123456789abcdef" for c in json_hash)
        
        # Verify the hash is consistent
        assert compute_json_hash(test_dict) == json_hash
        
        # Verify the hash changes when the dictionary changes
        modified_dict = test_dict.copy()
        modified_dict["key4"] = "new value"
        assert compute_json_hash(modified_dict) != json_hash
        
        # Verify the hash is the same regardless of key order
        reordered_dict = {"key2": 2, "key3": [1, 2, 3], "key1": "value1"}
        assert compute_json_hash(reordered_dict) == json_hash


class TestArtifactVersion:
    """Tests for the ArtifactVersion class."""
    
    def test_artifact_version_creation(self, tmp_path):
        """Test creating an ArtifactVersion."""
        # Create a test file
        test_file = tmp_path / "test_artifact.txt"
        test_file.write_text("Test artifact content")
        
        # Create an ArtifactVersion
        version = ArtifactVersion(
            artifact_path=test_file,
            artifact_type="text",
            job_id="job123",
            metadata={"key": "value"}
        )
        
        # Verify the attributes
        assert version.path == test_file
        assert version.type == "text"
        assert version.job_id == "job123"
        assert version.metadata == {"key": "value"}
        assert version.hash is not None
        assert version.version_id is not None
        assert version.parent_version_id is None
    
    def test_artifact_version_to_dict(self, tmp_path):
        """Test converting an ArtifactVersion to a dictionary."""
        # Create a test file
        test_file = tmp_path / "test_artifact.txt"
        test_file.write_text("Test artifact content")
        
        # Create an ArtifactVersion
        version = ArtifactVersion(
            artifact_path=test_file,
            artifact_type="text",
            job_id="job123",
            metadata={"key": "value"}
        )
        
        # Convert to dictionary
        version_dict = version.to_dict()
        
        # Verify the dictionary
        assert version_dict["path"] == str(test_file)
        assert version_dict["type"] == "text"
        assert version_dict["job_id"] == "job123"
        assert version_dict["metadata"] == {"key": "value"}
        assert version_dict["hash"] is not None
        assert version_dict["version_id"] is not None
        assert version_dict["parent_version_id"] is None
    
    def test_artifact_version_from_dict(self):
        """Test creating an ArtifactVersion from a dictionary."""
        # Create a dictionary
        version_dict = {
            "path": "/path/to/artifact.txt",
            "type": "text",
            "hash": "0123456789abcdef",
            "timestamp": "2023-01-01T12:00:00",
            "job_id": "job123",
            "version_id": "abcd1234",
            "parent_version_id": None,
            "metadata": {"key": "value"}
        }
        
        # Create an ArtifactVersion from the dictionary
        version = ArtifactVersion.from_dict(version_dict)
        
        # Verify the attributes
        assert str(version.path) == "/path/to/artifact.txt"
        assert version.type == "text"
        assert version.job_id == "job123"
        assert version.metadata == {"key": "value"}
        assert version.hash == "0123456789abcdef"
        assert version.version_id == "abcd1234"
        assert version.parent_version_id is None


class TestArtifactVersionRegistry:
    """Tests for the ArtifactVersionRegistry class."""
    
    @pytest.fixture
    def registry_dir(self):
        """Create a temporary directory for the registry."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)
    
    def test_registry_initialization(self, registry_dir):
        """Test initializing an ArtifactVersionRegistry."""
        # Create a registry
        registry = ArtifactVersionRegistry(registry_dir)
        
        # Verify the registry directory is created
        assert Path(registry_dir).exists()
        assert Path(registry_dir, "versions").exists()
    
    def test_register_artifact(self, registry_dir, tmp_path):
        """Test registering an artifact."""
        # Create a test file
        test_file = tmp_path / "test_artifact.txt"
        test_file.write_text("Test artifact content")
        
        # Create a registry
        registry = ArtifactVersionRegistry(registry_dir)
        
        # Register the artifact
        version = registry.register_artifact(
            artifact_path=test_file,
            artifact_type="text",
            job_id="job123",
            metadata={"key": "value"}
        )
        
        # Verify the version
        assert version.path == test_file
        assert version.type == "text"
        assert version.job_id == "job123"
        assert version.metadata == {"key": "value"}
        
        # Verify a copy was stored
        version_path = Path(registry_dir, "versions", f"{version.version_id}{test_file.suffix}")
        assert version_path.exists()
        
        # Verify the registry was updated
        assert str(test_file) in registry.registry
        assert len(registry.registry[str(test_file)]) == 1
    
    def test_get_artifact_versions(self, registry_dir, tmp_path):
        """Test getting all versions of an artifact."""
        # Create a test file
        test_file = tmp_path / "test_artifact.txt"
        test_file.write_text("Test artifact content")
        
        # Create a registry
        registry = ArtifactVersionRegistry(registry_dir)
        
        # Register the artifact multiple times
        version1 = registry.register_artifact(
            artifact_path=test_file,
            artifact_type="text",
            job_id="job123"
        )
        
        # Modify the file
        test_file.write_text("Modified content")
        
        version2 = registry.register_artifact(
            artifact_path=test_file,
            artifact_type="text",
            job_id="job123",
            parent_version_id=version1.version_id
        )
        
        # Get all versions
        versions = registry.get_artifact_versions(test_file)
        
        # Verify the versions
        assert len(versions) == 2
        assert versions[0].version_id == version1.version_id
        assert versions[1].version_id == version2.version_id
    
    def test_get_artifact_version(self, registry_dir, tmp_path):
        """Test getting a specific version of an artifact."""
        # Create a test file
        test_file = tmp_path / "test_artifact.txt"
        test_file.write_text("Test artifact content")
        
        # Create a registry
        registry = ArtifactVersionRegistry(registry_dir)
        
        # Register the artifact
        version = registry.register_artifact(
            artifact_path=test_file,
            artifact_type="text",
            job_id="job123"
        )
        
        # Get the version
        retrieved_version = registry.get_artifact_version(test_file, version.version_id)
        
        # Verify the version
        assert retrieved_version is not None
        assert retrieved_version.version_id == version.version_id
        
        # Try to get a nonexistent version
        nonexistent_version = registry.get_artifact_version(test_file, "nonexistent")
        assert nonexistent_version is None
    
    def test_rollback_artifact(self, registry_dir, tmp_path):
        """Test rolling back an artifact to a previous version."""
        # Create a test file
        test_file = tmp_path / "test_artifact.txt"
        original_content = "Original content"
        test_file.write_text(original_content)
        
        # Create a registry
        registry = ArtifactVersionRegistry(registry_dir)
        
        # Register the artifact
        version1 = registry.register_artifact(
            artifact_path=test_file,
            artifact_type="text",
            job_id="job123"
        )
        
        # Modify the file
        modified_content = "Modified content"
        test_file.write_text(modified_content)
        
        # Register the modified artifact
        version2 = registry.register_artifact(
            artifact_path=test_file,
            artifact_type="text",
            job_id="job123",
            parent_version_id=version1.version_id
        )
        
        # Verify the file has the modified content
        assert test_file.read_text() == modified_content
        
        # Roll back to the original version
        success = registry.rollback_artifact(test_file, version1.version_id)
        
        # Verify the rollback was successful
        assert success
        assert test_file.read_text() == original_content
        
        # Verify a new version was created for the rollback
        versions = registry.get_artifact_versions(test_file)
        assert len(versions) == 3
    
    def test_get_artifact_lineage(self, registry_dir, tmp_path):
        """Test getting the lineage of an artifact."""
        # Create a test file
        test_file = tmp_path / "test_artifact.txt"
        test_file.write_text("Original content")
        
        # Create a registry
        registry = ArtifactVersionRegistry(registry_dir)
        
        # Register the artifact multiple times with parent links
        version1 = registry.register_artifact(
            artifact_path=test_file,
            artifact_type="text",
            job_id="job123"
        )
        
        test_file.write_text("Modified content 1")
        version2 = registry.register_artifact(
            artifact_path=test_file,
            artifact_type="text",
            job_id="job123",
            parent_version_id=version1.version_id
        )
        
        test_file.write_text("Modified content 2")
        version3 = registry.register_artifact(
            artifact_path=test_file,
            artifact_type="text",
            job_id="job123",
            parent_version_id=version2.version_id
        )
        
        # Get the lineage
        lineage = registry.get_artifact_lineage(test_file)
        
        # Verify the lineage
        assert len(lineage) == 3
        assert lineage[0]["version_id"] == version3.version_id
        assert lineage[1]["version_id"] == version2.version_id
        assert lineage[2]["version_id"] == version1.version_id


if __name__ == "__main__":
    pytest.main()
