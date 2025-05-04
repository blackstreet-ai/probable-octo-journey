#!/usr/bin/env python
"""
Entry point script for the AI Video Pipeline.

This script provides a simple way to run the AI Video Pipeline
from the command line.
"""

import asyncio
import sys
from ai_video_pipeline.cli import main

if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
