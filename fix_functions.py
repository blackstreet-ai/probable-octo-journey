#!/usr/bin/env python
"""
Script to fix the duplicate function definitions in agent files.
"""

import os
import re
from pathlib import Path

def fix_function_definitions(file_path):
    """Fix duplicate function definitions in an agent file."""
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Fix pattern with duplicate function definitions
    pattern = r'{"type": "function", "function": {"name": "dummy_function", "description": "A placeholder function", "parameters": {"type": "object", "properties": {}}},\s+"function": {'
    replacement = '{"type": "function", "function": {'
    
    new_content = re.sub(pattern, replacement, content)
    
    if new_content != content:
        with open(file_path, 'w') as f:
            f.write(new_content)
        print(f"Fixed duplicate function definitions in {file_path}")
    else:
        print(f"No changes needed for {file_path}")

def main():
    """Fix function definitions in all agent files."""
    agents_dir = Path(__file__).parent / 'agents'
    
    for file_path in agents_dir.glob('*.py'):
        if file_path.name != '__init__.py':
            fix_function_definitions(file_path)

if __name__ == "__main__":
    main()
