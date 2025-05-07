#!/usr/bin/env python
"""
Script Validator: Ensures scripts follow proper formatting and structure.

This module provides functions to validate scripts against templates,
checking for required sections, appropriate lengths, and consistent formatting.
Includes advanced formatting fixes and revision capabilities.
"""

import logging
import re
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional, Union
import yaml
import textwrap

# Configure logging
logger = logging.getLogger(__name__)

class ScriptValidator:
    """
    Validates scripts against templates and formatting requirements.
    
    This class ensures scripts follow the correct template structure,
    have appropriate section lengths, include all required elements,
    and maintain consistent formatting. It also provides advanced
    formatting fixes and revision capabilities for addressing validation issues.
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
            "paragraph_line_threshold": 3,  # Threshold for identifying paragraphs (lines)
            "sentence_length_threshold": 40,  # Words per sentence threshold for readability
            "max_consecutive_short_sentences": 3  # Maximum consecutive short sentences
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
            if len(line) > self.rules["max_line_length"] and not line.strip().startswith("#") and not line.strip().startswith("-"):
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
        
        # Check for readability issues
        paragraphs = self._extract_paragraphs(script_content)
        for i, paragraph in enumerate(paragraphs):
            # Skip headings and list items
            if paragraph.startswith('#') or paragraph.strip().startswith('-'):
                continue
                
            # Check for very long sentences
            sentences = re.split(r'[.!?]\s+', paragraph)
            for j, sentence in enumerate(sentences):
                words = sentence.split()
                if len(words) > self.rules["sentence_length_threshold"]:
                    issues.append(f"Long sentence detected in paragraph {i+1} (contains {len(words)} words). " +
                                 f"Consider breaking it up for better readability.")
            
            # Check for too many consecutive short sentences
            short_sentence_count = 0
            for sentence in sentences:
                words = sentence.split()
                if len(words) < 8 and len(words) > 0:  # Arbitrary threshold for "short"
                    short_sentence_count += 1
                else:
                    short_sentence_count = 0
                    
                if short_sentence_count > self.rules["max_consecutive_short_sentences"]:
                    issues.append(f"Too many consecutive short sentences in paragraph {i+1}. " +
                                 f"Consider combining some for better flow.")
                    break
        
        return len(issues) == 0, issues
        
    def _extract_paragraphs(self, script_content: str) -> List[str]:
        """
        Extract paragraphs from the script content.
        
        Args:
            script_content: The content of the script
            
        Returns:
            List[str]: List of paragraphs
        """
        lines = script_content.split("\n")
        paragraphs = []
        current_paragraph = ""
        
        for line in lines:
            # If it's a heading or empty line, start a new paragraph
            if line.strip().startswith("#") or not line.strip():
                if current_paragraph:
                    paragraphs.append(current_paragraph.strip())
                    current_paragraph = ""
                if line.strip():
                    paragraphs.append(line.strip())
            # If it's a list item, treat it as its own paragraph
            elif line.strip().startswith("-") or line.strip().startswith("*"):
                if current_paragraph:
                    paragraphs.append(current_paragraph.strip())
                    current_paragraph = ""
                paragraphs.append(line.strip())
            # Otherwise, add to the current paragraph
            else:
                if current_paragraph:
                    current_paragraph += " " + line.strip()
                else:
                    current_paragraph = line.strip()
        
        # Add the last paragraph if it exists
        if current_paragraph:
            paragraphs.append(current_paragraph.strip())
        
        return paragraphs
    
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
        
        # Fix 3: Break long lines using textwrap for more intelligent line breaking
        max_length = self.rules["max_line_length"]
        paragraphs = self._extract_paragraphs(fixed_content)
        new_content = []
        
        for paragraph in paragraphs:
            # Skip headings, list items, and code blocks
            if paragraph.startswith('#') or paragraph.startswith('-') or paragraph.startswith('*') or paragraph.startswith('```'):
                new_content.append(paragraph)
                continue
                
            # Use textwrap for intelligent line breaking
            wrapped_lines = textwrap.fill(paragraph, width=max_length)
            new_content.append(wrapped_lines)
        
        # Reconstruct the script with proper line breaks between paragraphs
        fixed_content = "\n\n".join(new_content)
        
        # Fix 4: Improve readability of long sentences
        paragraphs = self._extract_paragraphs(fixed_content)
        new_content = []
        
        for paragraph in paragraphs:
            # Skip headings, list items, and code blocks
            if paragraph.startswith('#') or paragraph.startswith('-') or paragraph.startswith('*') or paragraph.startswith('```'):
                new_content.append(paragraph)
                continue
                
            # Split into sentences
            sentences = re.split(r'([.!?]\s+)', paragraph)
            
            # Recombine sentences with their punctuation
            reconstructed_sentences = []
            for i in range(0, len(sentences), 2):
                if i+1 < len(sentences):
                    reconstructed_sentences.append(sentences[i] + sentences[i+1])
                else:
                    reconstructed_sentences.append(sentences[i])
            
            # Check for very long sentences and break them up if possible
            improved_sentences = []
            for sentence in reconstructed_sentences:
                words = sentence.split()
                if len(words) > self.rules["sentence_length_threshold"]:
                    # Try to break at conjunctions or other natural break points
                    break_points = [" and ", ", ", "; ", ": "]
                    for break_point in break_points:
                        if break_point in sentence:
                            parts = sentence.split(break_point, 1)
                            if len(parts[0].split()) > 5:  # Ensure first part is substantial
                                if break_point == " and ":
                                    improved_sentences.append(parts[0] + ".")
                                    improved_sentences.append(parts[1].capitalize())
                                else:
                                    improved_sentences.append(parts[0] + break_point + parts[1])
                                break
                    else:  # No good break points found
                        improved_sentences.append(sentence)
                else:
                    improved_sentences.append(sentence)
            
            # Recombine the paragraph
            new_content.append(" ".join(improved_sentences))
        
        # Reconstruct the script with proper line breaks between paragraphs
        fixed_content = "\n\n".join(new_content)
        
        # Fix 5: Ensure proper spacing after punctuation
        fixed_content = re.sub(r'([.!?])([A-Z])', r'\1 \2', fixed_content)
        
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


def generate_revision_prompt(script_content: str, issues: List[str], script_format: str) -> str:
    """
    Generate a prompt for revising a script based on validation issues.
    
    Args:
        script_content: The content of the script to revise
        issues: List of validation issues to address
        script_format: The format of the script
        
    Returns:
        str: A prompt for revising the script
    """
    # Group issues by type for more structured feedback
    structure_issues = []
    length_issues = []
    metadata_issues = []
    formatting_issues = []
    readability_issues = []
    
    for issue in issues:
        if "section" in issue.lower() and "missing" in issue.lower():
            structure_issues.append(issue)
        elif "too short" in issue.lower() or "too long" in issue.lower():
            length_issues.append(issue)
        elif "metadata" in issue.lower():
            metadata_issues.append(issue)
        elif "line" in issue.lower() and "exceeds" in issue.lower():
            formatting_issues.append(issue)
        elif "sentence" in issue.lower() or "paragraph" in issue.lower():
            readability_issues.append(issue)
        else:
            formatting_issues.append(issue)
    
    # Build the revision prompt
    prompt = f"""Please revise the following script to address these validation issues:

```
{script_content}
```

"""
    
    if structure_issues:
        prompt += "\n### Structure Issues\n"
        for issue in structure_issues:
            prompt += f"- {issue}\n"
    
    if length_issues:
        prompt += "\n### Length Issues\n"
        for issue in length_issues:
            prompt += f"- {issue}\n"
    
    if metadata_issues:
        prompt += "\n### Metadata Issues\n"
        for issue in metadata_issues:
            prompt += f"- {issue}\n"
    
    if formatting_issues:
        prompt += "\n### Formatting Issues\n"
        for issue in formatting_issues:
            prompt += f"- {issue}\n"
    
    if readability_issues:
        prompt += "\n### Readability Issues\n"
        for issue in readability_issues:
            prompt += f"- {issue}\n"
    
    prompt += f"\nPlease maintain the {script_format} script format while addressing these issues. Pay special attention to:\n"
    
    if structure_issues:
        prompt += "\n- Adding any missing required sections\n"
    if length_issues:
        prompt += "\n- Adjusting section lengths to meet requirements\n"
    if metadata_issues:
        prompt += "\n- Completing all required metadata fields\n"
    if formatting_issues:
        prompt += "\n- Fixing line length and formatting issues\n"
    if readability_issues:
        prompt += "\n- Improving sentence structure and readability\n"
    
    prompt += "\nReturn the complete revised script in proper markdown format."
    
    return prompt


def create_validation_feedback_loop(script_content: str, script_format: str, max_attempts: int = 3) -> Tuple[str, bool, List[str]]:
    """
    Create a feedback loop for script validation and revision.
    
    This function attempts to validate and fix a script multiple times,
    generating specific revision prompts based on validation issues.
    
    Args:
        script_content: The content of the script to validate and revise
        script_format: The format of the script
        max_attempts: Maximum number of validation/revision attempts
        
    Returns:
        Tuple[str, bool, List[str]]: (final_script, is_valid, remaining_issues)
    """
    current_script = script_content
    attempt = 0
    
    while attempt < max_attempts:
        # Validate the current script
        is_valid, issues = validate_script(current_script, script_format)
        
        # If valid, return the script
        if is_valid:
            return current_script, True, []
        
        # Try to fix common issues automatically
        fixed_script = fix_script_formatting(current_script)
        
        # Check if the fixes resolved the issues
        is_valid_after_fix, remaining_issues = validate_script(fixed_script, script_format)
        
        # If valid after fixes, return the fixed script
        if is_valid_after_fix:
            return fixed_script, True, []
        
        # Generate a revision prompt for the remaining issues
        # Note: In a real implementation, this would be sent to an LLM for revision
        # For now, we'll just log it and return the best version we have
        revision_prompt = generate_revision_prompt(fixed_script, remaining_issues, script_format)
        logger.info(f"Generated revision prompt for attempt {attempt+1}:\n{revision_prompt}")
        
        # In a real implementation, you would send this prompt to an LLM and get a revised script
        # For now, we'll just use the fixed script as our best attempt
        current_script = fixed_script
        attempt += 1
    
    # Return the best version we have after max attempts
    return current_script, False, remaining_issues
