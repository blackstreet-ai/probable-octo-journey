#!/usr/bin/env python
"""
Observability tools for the AI Video Automation Pipeline.

This module provides functions for logging, event tracking, and metrics collection
to enable observability of the AI Video Automation Pipeline.
"""

import functools
import json
import logging
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Callable, Optional, Union

# Configure logging
logger = logging.getLogger(__name__)

# Default event log file
DEFAULT_EVENT_LOG_FILE = os.getenv(
    "EVENT_LOG_FILE", 
    str(Path(__file__).parent.parent / "logs" / "events.jsonl")
)

def log_event(event_name: str, data: Dict[str, Any], 
              event_log_file: Optional[str] = None) -> None:
    """
    Log an event to the event log file.
    
    Args:
        event_name: Name of the event
        data: Event data
        event_log_file: Path to the event log file (optional)
    """
    try:
        # Create event record
        event = {
            "timestamp": datetime.now().isoformat(),
            "event": event_name,
            "data": data
        }
        
        # Determine log file path
        log_file = event_log_file or DEFAULT_EVENT_LOG_FILE
        
        # Ensure directory exists
        Path(log_file).parent.mkdir(parents=True, exist_ok=True)
        
        # Append to log file
        with open(log_file, "a") as f:
            f.write(json.dumps(event) + "\n")
            
        logger.debug(f"Logged event: {event_name}")
        
    except Exception as e:
        logger.error(f"Failed to log event {event_name}: {str(e)}")


def track_duration(func: Callable) -> Callable:
    """
    Decorator to track the duration of a function execution.
    
    Args:
        func: Function to track
        
    Returns:
        Callable: Wrapped function
    """
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        # Get function name
        func_name = func.__name__
        
        # Extract job_id from context if available
        context = kwargs.get("context", {})
        if not context and len(args) > 0 and isinstance(args[0], dict):
            context = args[0]
        
        job_id = context.get("job_id", "unknown")
        
        # Log start event
        log_event(f"{func_name}_started", {"job_id": job_id})
        
        # Record start time
        start_time = time.time()
        
        try:
            # Execute the function
            result = await func(*args, **kwargs)
            
            # Calculate duration
            duration = time.time() - start_time
            
            # Log completion event
            log_event(f"{func_name}_completed", {
                "job_id": job_id,
                "duration_seconds": duration
            })
            
            return result
            
        except Exception as e:
            # Calculate duration
            duration = time.time() - start_time
            
            # Log error event
            log_event(f"{func_name}_failed", {
                "job_id": job_id,
                "duration_seconds": duration,
                "error": str(e)
            })
            
            # Re-raise the exception
            raise
    
    return wrapper


class MetricsCollector:
    """
    Collector for metrics about the AI Video Automation Pipeline.
    """
    
    def __init__(self, job_id: str, output_dir: Optional[str] = None):
        """
        Initialize the MetricsCollector.
        
        Args:
            job_id: The ID of the job
            output_dir: Directory to save metrics (optional)
        """
        self.job_id = job_id
        self.metrics = {
            "job_id": job_id,
            "start_time": datetime.now().isoformat(),
            "durations": {},
            "counts": {},
            "sizes": {}
        }
        
        # Determine output directory
        if output_dir:
            self.output_dir = Path(output_dir)
        else:
            self.output_dir = Path(__file__).parent.parent / "logs" / "metrics"
        
        # Ensure directory exists
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def record_duration(self, step_name: str, duration_seconds: float) -> None:
        """
        Record the duration of a step.
        
        Args:
            step_name: Name of the step
            duration_seconds: Duration in seconds
        """
        self.metrics["durations"][step_name] = duration_seconds
    
    def increment_count(self, counter_name: str, increment: int = 1) -> None:
        """
        Increment a counter.
        
        Args:
            counter_name: Name of the counter
            increment: Amount to increment by (default: 1)
        """
        current = self.metrics["counts"].get(counter_name, 0)
        self.metrics["counts"][counter_name] = current + increment
    
    def record_size(self, item_name: str, size_bytes: int) -> None:
        """
        Record the size of an item.
        
        Args:
            item_name: Name of the item
            size_bytes: Size in bytes
        """
        self.metrics["sizes"][item_name] = size_bytes
    
    def save(self) -> str:
        """
        Save the metrics to a file.
        
        Returns:
            str: Path to the saved metrics file
        """
        # Add end time
        self.metrics["end_time"] = datetime.now().isoformat()
        
        # Calculate total duration
        start = datetime.fromisoformat(self.metrics["start_time"])
        end = datetime.fromisoformat(self.metrics["end_time"])
        self.metrics["total_duration_seconds"] = (end - start).total_seconds()
        
        # Save to file
        metrics_file = self.output_dir / f"metrics_{self.job_id}.json"
        with open(metrics_file, "w") as f:
            json.dump(self.metrics, f, indent=2)
        
        return str(metrics_file)
