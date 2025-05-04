#!/usr/bin/env python
"""
Quick script to fix the tools configuration in all agent files.
"""

import os
import re
from pathlib import Path

def fix_tools_config(file_path):
    """Fix the tools configuration in an agent file."""
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Check if this file has the empty function tools configuration
    pattern1 = r'tools=\[\{"type": "function"\}\].*?# No specific tools needed for this agent'
    if re.search(pattern1, content):
        # Replace with code_interpreter
        replacement = 'tools=[{"type": "code_interpreter"}]  # Using code_interpreter instead of empty function'
        new_content = re.sub(pattern1, replacement, content)
        
        with open(file_path, 'w') as f:
            f.write(new_content)
        print(f"Updated {file_path} - replaced empty function with code_interpreter")
        return
    
    # Check if this file has function tools with missing function definition
    pattern2 = r'\{\s*"type": "function",\s*(?!"function":)'
    if re.search(pattern2, content):
        # Add a proper function definition
        new_content = re.sub(
            pattern2,
            '{"type": "function", "function": {"name": "dummy_function", "description": "A placeholder function", "parameters": {"type": "object", "properties": {}}}, ',
            content
        )
        
        with open(file_path, 'w') as f:
            f.write(new_content)
        print(f"Updated {file_path} - added missing function definition")
        return
    
    print(f"No changes needed for {file_path}")

def main():
    """Fix tools configuration in all agent files."""
    agents_dir = Path(__file__).parent / 'agents'
    
    for file_path in agents_dir.glob('*.py'):
        if file_path.name != '__init__.py':
            fix_tools_config(file_path)

if __name__ == "__main__":
    main()
