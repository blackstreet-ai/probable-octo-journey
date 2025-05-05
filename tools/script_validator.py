#!/usr/bin/env python
"""
Script Validator: Ensures scripts follow proper formatting and structure.

This module provides functions to validate scripts against templates,
checking for required sections, appropriate lengths, and consistent formatting.
"""

import logging
import re
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional
import yaml

# Configure logging
logger = logging.getLogger(__name__)

class ScriptValidator:
    """
    Validates scripts against templates and formatting requirements.
    
    This class ensures scripts follow the correct template structure,
    have appropriate section lengths, include all required elements,
    and maintain consistent formatting.
    """
    
    def __init__(self, templates_dir: Optional[str] = None):
        """
        Initialize the ScriptValidator.
        
        Args:
            templates_dir: Optional path to templates directory
        """
        if templates_dir:
            self.templates_dir = Path(templates_dir)
        else:
            self.templates_dir = Path(__file__).parent.parent / "prompts" / "templates"
        
        self.templates = self._load_templates()
        
        # Define validation rules
        self.rules = {
            "min_section_length": 50,  # Minimum characters per section
            "max_section_length": 2000,  # Maximum characters per section
            "required_metadata": ["target audience", "tone", "duration"],
            "min_sections": 3,  # Minimum number of sections (intro, content, conclusion)
            "max_line_length": 100,  # Maximum characters per line
        }
    
    def _load_templates(self) -> Dict[str, Any]:
        """
        Load all script templates.
        
        Returns:
            Dict[str, Any]: Dictionary of templates by format type
        """
        templates = {}
        
        try:
            for template_file in self.templates_dir.glob("*.yaml"):
                template_name = template_file.stem
                with open(template_file, "r") as f:
                    templates[template_name] = yaml.safe_load(f)
            logger.debug(f"Loaded {len(templates)} script templates for validation")
        except Exception as e:
            logger.error(f"Failed to load script templates: {str(e)}")
            raise
            
        return templates
    
    def validate_script(self, script_content: str, script_format: str) -> Tuple[bool, List[str]]:
        """
        Validate a script against its template and formatting rules.
        
        Args:
            script_content: The content of the script to validate
            script_format: The format of the script (narration, interview, etc.)
            
        Returns:
            Tuple[bool, List[str]]: (is_valid, list_of_issues)
        """
        if script_format not in self.templates:
            return False, [f"Unknown script format: {script_format}"]
        
        template = self.templates[script_format]
        issues = []
        
        # Check 1: Validate basic structure (headings)
        structure_valid, structure_issues = self._validate_structure(script_content, script_format)
        issues.extend(structure_issues)
        
        # Check 2: Validate section lengths
        length_valid, length_issues = self._validate_section_lengths(script_content)
        issues.extend(length_issues)
        
        # Check 3: Validate metadata
        metadata_valid, metadata_issues = self._validate_metadata(script_content)
        issues.extend(metadata_issues)
        
        # Check 4: Validate formatting
        format_valid, format_issues = self._validate_formatting(script_content)
        issues.extend(format_issues)
        
        # Script is valid if there are no issues
        is_valid = len(issues) == 0
        
        return is_valid, issues
    
    def _validate_structure(self, script_content: str, script_format: str) -> Tuple[bool, List[str]]:
        """
        Validate that the script follows the template structure.
        
        Args:
            script_content: The content of the script
            script_format: The format of the script
            
        Returns:
            Tuple[bool, List[str]]: (is_valid, list_of_issues)
        """
        issues = []
        template = self.templates[script_format]
        
        # Extract expected sections from the template structure
        expected_sections = []
        structure_lines = template.get("structure", "").split("\n")
        for line in structure_lines:
            if line.strip().startswith("#"):
                # Count the number of # to determine heading level
                level = len(re.match(r'^(#+)', line.strip()).group(1))
                # Extract the section name, removing any [placeholders]
                section_name = re.sub(r'\[.*?\]', '', line.strip('#').strip()).strip()
                if section_name and not section_name.lower() in ['metadata']:  # Skip metadata section
                    expected_sections.append((level, section_name.lower()))
        
        # Extract actual sections from the script
        actual_sections = []
        for line in script_content.split("\n"):
            if line.strip().startswith("#"):
                level = len(re.match(r'^(#+)', line.strip()).group(1))
                section_name = line.strip('#').strip().lower()
                actual_sections.append((level, section_name))
        
        # Check if we have enough sections
        if len(actual_sections) < self.rules["min_sections"]:
            issues.append(f"Script has too few sections ({len(actual_sections)}). " +
                          f"Minimum required: {self.rules['min_sections']}")
        
        # Check for required sections
        for level, expected_section in expected_sections:
            found = False
            for actual_level, actual_section in actual_sections:
                # Check if the actual section contains the expected section name
                # This allows for some flexibility in section naming
                if expected_section in actual_section:
                    found = True
                    break
            
            if not found:
                issues.append(f"Missing required section: {expected_section}")
        
        return len(issues) == 0, issues
    
    def _validate_section_lengths(self, script_content: str) -> Tuple[bool, List[str]]:
        """
        Validate that each section has an appropriate length.
        
        Args:
            script_content: The content of the script
            
        Returns:
            Tuple[bool, List[str]]: (is_valid, list_of_issues)
        """
        issues = []
        
        # Split the script into sections
        sections = []
        current_section = {"name": "", "content": ""}
        
        for line in script_content.split("\n"):
            if line.strip().startswith("#"):
                # Save the previous section if it exists
                if current_section["name"]:
                    sections.append(current_section)
                
                # Start a new section
                current_section = {
                    "name": line.strip(),
                    "content": ""
                }
            else:
                current_section["content"] += line + "\n"
        
        # Add the last section
        if current_section["name"]:
            sections.append(current_section)
        
        # Check each section's length
        for section in sections:
            content_length = len(section["content"].strip())
            
            if content_length < self.rules["min_section_length"]:
                issues.append(f"Section '{section['name']}' is too short ({content_length} chars). " +
                             f"Minimum: {self.rules['min_section_length']} chars")
            
            if content_length > self.rules["max_section_length"]:
                issues.append(f"Section '{section['name']}' is too long ({content_length} chars). " +
                             f"Maximum: {self.rules['max_section_length']} chars")
        
        return len(issues) == 0, issues
    
    def _validate_metadata(self, script_content: str) -> Tuple[bool, List[str]]:
        """
        Validate that the script includes required metadata.
        
        Args:
            script_content: The content of the script
            
        Returns:
            Tuple[bool, List[str]]: (is_valid, list_of_issues)
        """
        issues = []
        
        # Look for metadata section
        metadata_section = ""
        in_metadata = False
        
        for line in script_content.split("\n"):
            if line.strip().startswith("## METADATA") or line.strip().lower() == "## metadata":
                in_metadata = True
                continue
            
            if in_metadata and line.strip().startswith("#"):
                # End of metadata section
                break
            
            if in_metadata:
                metadata_section += line + "\n"
        
        if not metadata_section:
            issues.append("Missing METADATA section")
            return False, issues
        
        # Check for required metadata fields
        for field in self.rules["required_metadata"]:
            if not re.search(rf'{field}', metadata_section, re.IGNORECASE):
                issues.append(f"Missing required metadata: {field}")
        
        return len(issues) == 0, issues
    
    def _validate_formatting(self, script_content: str) -> Tuple[bool, List[str]]:
        """
        Validate that the script follows formatting guidelines.
        
        Args:
            script_content: The content of the script
            
        Returns:
            Tuple[bool, List[str]]: (is_valid, list_of_issues)
        """
        issues = []
        
        # Check line length
        for i, line in enumerate(script_content.split("\n")):
            if len(line) > self.rules["max_line_length"]:
                issues.append(f"Line {i+1} exceeds maximum length ({len(line)} chars). " +
                             f"Maximum: {self.rules['max_line_length']} chars")
        
        # Check for consistent heading format (##, not #, for sections)
        heading_levels = {}
        for line in script_content.split("\n"):
            if line.strip().startswith("#"):
                level = len(re.match(r'^(#+)', line.strip()).group(1))
                heading = line.strip('#').strip()
                
                if heading in heading_levels and heading_levels[heading] != level:
                    issues.append(f"Inconsistent heading level for '{heading}'")
                
                heading_levels[heading] = level
        
        # Check for proper markdown formatting
        if "```" in script_content and script_content.count("```") % 2 != 0:
            issues.append("Unmatched code block markers (```)")
        
        return len(issues) == 0, issues
    
    def fix_common_issues(self, script_content: str) -> str:
        """
        Attempt to fix common formatting issues in the script.
        
        Args:
            script_content: The content of the script
            
        Returns:
            str: The fixed script content
        """
        fixed_content = script_content
        
        # Fix 1: Ensure consistent heading levels
        lines = fixed_content.split("\n")
        title_line = None
        
        # Find the title (first heading)
        for i, line in enumerate(lines):
            if line.strip().startswith("#"):
                title_line = i
                break
        
        if title_line is not None:
            # Ensure title is H1
            if not lines[title_line].startswith("# "):
                lines[title_line] = "# " + lines[title_line].lstrip("#").strip()
            
            # Ensure sections are H2
            for i in range(title_line + 1, len(lines)):
                if lines[i].strip().startswith("#") and not lines[i].strip().startswith("## "):
                    # If it's H1, make it H2
                    if lines[i].startswith("# "):
                        lines[i] = "#" + lines[i]
                    # If it's H3 or deeper, leave it alone
        
        fixed_content = "\n".join(lines)
        
        # Fix 2: Add metadata section if missing
        if "## METADATA" not in fixed_content and "## metadata" not in fixed_content:
            metadata = "\n\n## METADATA\n- Target audience: \n- Tone: \n- Estimated duration: \n- Sources: \n"
            fixed_content += metadata
        
        # Fix 3: Break long lines
        max_length = self.rules["max_line_length"]
        lines = fixed_content.split("\n")
        new_lines = []
        
        for line in lines:
            if len(line) <= max_length or line.strip().startswith("#") or line.strip().startswith("-"):
                new_lines.append(line)
            else:
                # Try to break at a space
                words = line.split(" ")
                current_line = ""
                
                for word in words:
                    if len(current_line) + len(word) + 1 <= max_length:
                        if current_line:
                            current_line += " " + word
                        else:
                            current_line = word
                    else:
                        new_lines.append(current_line)
                        current_line = word
                
                if current_line:
                    new_lines.append(current_line)
        
        fixed_content = "\n".join(new_lines)
        
        return fixed_content


def validate_script(script_content: str, script_format: str) -> Tuple[bool, List[str]]:
    """
    Validate a script against its template and formatting rules.
    
    Args:
        script_content: The content of the script to validate
        script_format: The format of the script (narration, interview, etc.)
        
    Returns:
        Tuple[bool, List[str]]: (is_valid, list_of_issues)
    """
    validator = ScriptValidator()
    return validator.validate_script(script_content, script_format)


def fix_script_formatting(script_content: str) -> str:
    """
    Attempt to fix common formatting issues in the script.
    
    Args:
        script_content: The content of the script
        
    Returns:
        str: The fixed script content
    """
    validator = ScriptValidator()
    return validator.fix_common_issues(script_content)
