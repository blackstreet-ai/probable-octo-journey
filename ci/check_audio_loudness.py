#!/usr/bin/env python3
"""
Audio Loudness Check Script for CI

This script checks if audio files meet the required loudness standards.
It can be used in a CI pipeline to verify that mixed audio files meet
the -14 LUFS standard.
"""

import os
import sys
import json
import argparse
import subprocess
import logging
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def measure_loudness(file_path: str) -> Tuple[bool, float]:
    """
    Measure the integrated loudness of an audio file in LUFS.
    
    Args:
        file_path: Path to the audio file
        
    Returns:
        Tuple[bool, float]: Success flag and loudness in LUFS
    """
    command = [
        "ffmpeg",
        "-i", file_path,
        "-af", "loudnorm=print_format=json",
        "-f", "null",
        "-"
    ]
    
    try:
        process = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False
        )
        
        if process.returncode != 0:
            logger.error(f"Error measuring audio loudness: {process.stderr}")
            return False, -24.0  # Default value
        
        # Extract the JSON part from stderr
        stderr = process.stderr
        json_start = stderr.find("{")
        json_end = stderr.rfind("}") + 1
        
        if json_start >= 0 and json_end > json_start:
            json_str = stderr[json_start:json_end]
            data = json.loads(json_str)
            return True, float(data.get("input_i", "-24.0"))
        else:
            logger.error("Could not find JSON data in ffmpeg output")
            return False, -24.0
            
    except Exception as e:
        logger.error(f"Error running ffmpeg command: {e}")
        return False, -24.0


def check_audio_file(file_path: str, target_lufs: float, tolerance: float) -> Tuple[bool, float, str]:
    """
    Check if an audio file meets the loudness standard.
    
    Args:
        file_path: Path to the audio file
        target_lufs: Target loudness in LUFS
        tolerance: Tolerance in LUFS
        
    Returns:
        Tuple[bool, float, str]: Pass flag, measured loudness, and message
    """
    if not os.path.exists(file_path):
        return False, 0.0, f"File does not exist: {file_path}"
    
    success, loudness = measure_loudness(file_path)
    
    if not success:
        return False, loudness, f"Failed to measure loudness for {file_path}"
    
    min_lufs = target_lufs - tolerance
    max_lufs = target_lufs + tolerance
    
    if min_lufs <= loudness <= max_lufs:
        return True, loudness, f"PASS: {file_path} loudness is {loudness:.2f} LUFS (target: {target_lufs:.2f} ± {tolerance:.2f})"
    else:
        return False, loudness, f"FAIL: {file_path} loudness is {loudness:.2f} LUFS (target: {target_lufs:.2f} ± {tolerance:.2f})"


def check_directory(directory: str, target_lufs: float, tolerance: float, extensions: List[str]) -> Tuple[int, int, List[str]]:
    """
    Check all audio files in a directory.
    
    Args:
        directory: Directory to check
        target_lufs: Target loudness in LUFS
        tolerance: Tolerance in LUFS
        extensions: List of file extensions to check
        
    Returns:
        Tuple[int, int, List[str]]: Number of files checked, number of files that passed, and list of messages
    """
    if not os.path.isdir(directory):
        return 0, 0, [f"Directory does not exist: {directory}"]
    
    messages = []
    files_checked = 0
    files_passed = 0
    
    for ext in extensions:
        for file_path in Path(directory).glob(f"**/*.{ext}"):
            files_checked += 1
            passed, loudness, message = check_audio_file(str(file_path), target_lufs, tolerance)
            messages.append(message)
            
            if passed:
                files_passed += 1
    
    return files_checked, files_passed, messages


def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="Check audio files for loudness standards")
    parser.add_argument("--file", "-f", help="Path to audio file to check")
    parser.add_argument("--directory", "-d", help="Directory containing audio files to check")
    parser.add_argument("--target", "-t", type=float, default=-14.0, help="Target loudness in LUFS (default: -14.0)")
    parser.add_argument("--tolerance", type=float, default=1.0, help="Tolerance in LUFS (default: 1.0)")
    parser.add_argument("--extensions", default="wav,mp3", help="Comma-separated list of file extensions to check (default: wav,mp3)")
    args = parser.parse_args()
    
    if not args.file and not args.directory:
        parser.error("Either --file or --directory must be specified")
    
    extensions = [ext.strip() for ext in args.extensions.split(",")]
    
    if args.file:
        passed, loudness, message = check_audio_file(args.file, args.target, args.tolerance)
        print(message)
        sys.exit(0 if passed else 1)
    
    if args.directory:
        files_checked, files_passed, messages = check_directory(args.directory, args.target, args.tolerance, extensions)
        
        for message in messages:
            print(message)
        
        print(f"\nSummary: {files_passed}/{files_checked} files passed the loudness check")
        print(f"Target: {args.target:.2f} LUFS ± {args.tolerance:.2f}")
        
        if files_checked == 0:
            print("No audio files found")
            sys.exit(1)
        
        if files_passed < files_checked:
            print("Some files failed the loudness check")
            sys.exit(1)
        
        print("All files passed the loudness check")
        sys.exit(0)


if __name__ == "__main__":
    main()
