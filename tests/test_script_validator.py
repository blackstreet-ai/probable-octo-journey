#!/usr/bin/env python
"""
Unit tests for the script validator module.

Tests the functionality of the script validator including structure validation,
section length validation, metadata validation, and formatting validation.
"""

import os
import pytest
from unittest.mock import patch, mock_open
from pathlib import Path

from tools.script_validator import ScriptValidator, validate_script, fix_script_formatting


@pytest.fixture
def mock_templates():
    """Mock template data."""
    return {
        "narration": {
            "name": "Narration Script Template",
            "structure": "# [TITLE]\n## INTRODUCTION\n## MAIN CONTENT\n## CONCLUSION\n## METADATA"
        },
        "interview": {
            "name": "Interview Script Template",
            "structure": "# [TITLE]\n## METADATA\n## INTRO\n## SEGMENT 1\n## SEGMENT 2\n## CONCLUSION"
        }
    }


@pytest.fixture
def validator(mock_templates):
    """Create a ScriptValidator instance with mocked templates."""
    with patch.object(ScriptValidator, '_load_templates', return_value=mock_templates):
        validator = ScriptValidator()
        return validator


@pytest.fixture
def valid_script():
    """Create a valid narration script."""
    return """# Sample Video Title

## INTRODUCTION
This is an introduction that is long enough to meet the minimum section length requirements.
It provides context and sets up the main content of the video.

## MAIN CONTENT
This is the main content section that provides detailed information about the topic.
It includes multiple paragraphs and covers all the key points.
This section is substantial enough to meet the length requirements.

## CONCLUSION
This is the conclusion that summarizes the key points and provides a call to action.
It wraps up the video nicely and leaves the viewer with something to think about.

## METADATA
- Target audience: General public
- Tone: Informative and engaging
- Estimated duration: 5 minutes
- Sources: Research papers, expert interviews
"""


@pytest.fixture
def invalid_script():
    """Create an invalid script with various issues."""
    return """# Sample Video
## intro
Too short.

## content
Also too short.

# Wrong heading level for a section

No metadata section.
"""


class TestScriptValidator:
    """Test cases for the ScriptValidator class."""

    def test_initialization(self, validator):
        """Test that the ScriptValidator initializes correctly."""
        assert validator is not None
        assert validator.templates is not None
        assert "narration" in validator.templates
        assert "interview" in validator.templates
        assert validator.rules is not None

    def test_validate_valid_script(self, validator, valid_script):
        """Test validation of a valid script."""
        is_valid, issues = validator.validate_script(valid_script, "narration")
        assert is_valid
        assert len(issues) == 0

    def test_validate_invalid_script(self, validator, invalid_script):
        """Test validation of an invalid script."""
        is_valid, issues = validator.validate_script(invalid_script, "narration")
        assert not is_valid
        assert len(issues) > 0
        
        # Check for specific issues
        section_length_issue = any("too short" in issue.lower() for issue in issues)
        metadata_issue = any("metadata" in issue.lower() for issue in issues)
        
        assert section_length_issue
        assert metadata_issue

    def test_validate_unknown_format(self, validator, valid_script):
        """Test validation with an unknown script format."""
        is_valid, issues = validator.validate_script(valid_script, "unknown_format")
        assert not is_valid
        assert len(issues) == 1
        assert "Unknown script format" in issues[0]

    def test_fix_script_formatting(self, validator, invalid_script):
        """Test fixing common formatting issues."""
        fixed_script = validator.fix_common_issues(invalid_script)
        
        # Check if fixes were applied
        assert "## METADATA" in fixed_script
        
        # Validate the fixed script
        is_valid, issues = validator.validate_script(fixed_script, "narration")
        
        # It might still have issues (like section length), but should have fewer
        assert len(issues) < len(validator.validate_script(invalid_script, "narration")[1])

    def test_validate_structure(self, validator):
        """Test structure validation specifically."""
        script = """# Title
## INTRODUCTION
Content
## CONCLUSION
Content
## METADATA
- Target audience: General
"""
        is_valid, issues = validator._validate_structure(script, "narration")
        assert not is_valid  # Missing MAIN CONTENT section
        assert any("Missing required section" in issue for issue in issues)

    def test_validate_section_lengths(self, validator):
        """Test section length validation."""
        script = """# Title
## INTRODUCTION
Too short.
## MAIN CONTENT
Also too short.
## CONCLUSION
And this too.
## METADATA
- Target audience: General
"""
        is_valid, issues = validator._validate_section_lengths(script)
        assert not is_valid
        assert len(issues) == 3  # Three sections that are too short
        assert all("too short" in issue for issue in issues)

    def test_validate_metadata(self, validator):
        """Test metadata validation."""
        script = """# Title
## INTRODUCTION
Content
## MAIN CONTENT
Content
## CONCLUSION
Content
## METADATA
- Missing required fields
"""
        is_valid, issues = validator._validate_metadata(script)
        assert not is_valid
        assert any("target audience" in issue.lower() for issue in issues)


def test_module_functions():
    """Test the module-level functions."""
    with patch('tools.script_validator.ScriptValidator') as mock_validator_class:
        mock_validator = mock_validator_class.return_value
        mock_validator.validate_script.return_value = (True, [])
        mock_validator.fix_common_issues.return_value = "Fixed script"
        
        # Test validate_script function
        result = validate_script("Script content", "narration")
        assert result == (True, [])
        mock_validator.validate_script.assert_called_once()
        
        # Test fix_script_formatting function
        result = fix_script_formatting("Script content")
        assert result == "Fixed script"
        mock_validator.fix_common_issues.assert_called_once()
