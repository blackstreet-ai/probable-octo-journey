"""
Observability module for the AI Video Pipeline.

This module provides tools for logging, event tracking, and metrics collection
to improve the observability of the pipeline.
"""

import os
import sys
import json
import logging
import time
from typing import Dict, Any, Optional, List, Union, Callable
from pathlib import Path
from datetime import datetime
from functools import wraps
import traceback
import uuid

from pydantic import BaseModel, Field


class EventType:
    """Event types for pipeline observability."""
    AGENT_START = "agent_start"
    AGENT_COMPLETE = "agent_complete"
    AGENT_ERROR = "agent_error"
    ASSET_CREATED = "asset_created"
    ASSET_UPDATED = "asset_updated"
    API_CALL_START = "api_call_start"
    API_CALL_COMPLETE = "api_call_complete"
    API_CALL_ERROR = "api_call_error"
    PIPELINE_START = "pipeline_start"
    PIPELINE_COMPLETE = "pipeline_complete"
    PIPELINE_ERROR = "pipeline_error"
    QC_ISSUE = "qc_issue"
    COMPLIANCE_ISSUE = "compliance_issue"


class Event(BaseModel):
    """Model for pipeline events."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())
    event_type: str
    component: str
    job_id: Optional[str] = None
    message: str
    data: Dict[str, Any] = Field(default_factory=dict)
    parent_event_id: Optional[str] = None


class PipelineObserver:
    """
    Observer for the AI Video Pipeline that handles logging and event tracking.
    
    This class provides methods for:
    1. Configuring logging to console and file
    2. Tracking events throughout the pipeline
    3. Recording metrics for analysis
    4. Providing decorators for timing and error tracking
    """
    
    def __init__(
        self,
        log_level: int = logging.INFO,
        log_to_console: bool = True,
        log_to_file: bool = True,
        log_dir: Optional[Path] = None,
        event_log_enabled: bool = True
    ):
        """
        Initialize the Pipeline Observer.
        
        Args:
            log_level: Logging level (default: INFO)
            log_to_console: Whether to log to console
            log_to_file: Whether to log to file
            log_dir: Directory for log files (default: ./logs)
            event_log_enabled: Whether to record events to JSONL file
        """
        self.log_level = log_level
        self.log_to_console = log_to_console
        self.log_to_file = log_to_file
        self.log_dir = log_dir or Path("./logs")
        self.event_log_enabled = event_log_enabled
        self.events: List[Event] = []
        
        # Set up logging
        self._setup_logging()
        
        # Logger instance for this class
        self.logger = logging.getLogger(__name__)
    
    def _setup_logging(self) -> None:
        """Set up logging configuration."""
        # Create root logger
        root_logger = logging.getLogger()
        root_logger.setLevel(self.log_level)
        
        # Remove existing handlers
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)
        
        # Create formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        
        # Add console handler if enabled
        if self.log_to_console:
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setFormatter(formatter)
            root_logger.addHandler(console_handler)
        
        # Add file handler if enabled
        if self.log_to_file:
            self.log_dir.mkdir(parents=True, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            log_file = self.log_dir / f"pipeline_{timestamp}.log"
            
            file_handler = logging.FileHandler(log_file)
            file_handler.setFormatter(formatter)
            root_logger.addHandler(file_handler)
            
            self.logger.info(f"Logging to file: {log_file}")
        
        # Set up event log file if enabled
        if self.event_log_enabled:
            self.event_log_file = self.log_dir / f"events_{timestamp}.jsonl"
            self.logger.info(f"Event log file: {self.event_log_file}")
    
    def record_event(
        self,
        event_type: str,
        component: str,
        message: str,
        job_id: Optional[str] = None,
        data: Optional[Dict[str, Any]] = None,
        parent_event_id: Optional[str] = None
    ) -> Event:
        """
        Record an event in the pipeline.
        
        Args:
            event_type: Type of event (see EventType class)
            component: Component that generated the event
            message: Event message
            job_id: Optional job ID associated with the event
            data: Optional data associated with the event
            parent_event_id: Optional ID of the parent event
        
        Returns:
            Event: The recorded event
        """
        event = Event(
            event_type=event_type,
            component=component,
            message=message,
            job_id=job_id,
            data=data or {},
            parent_event_id=parent_event_id
        )
        
        # Add to in-memory event list
        self.events.append(event)
        
        # Log the event
        log_level = logging.ERROR if "error" in event_type.lower() else logging.INFO
        self.logger.log(log_level, f"EVENT: {event.event_type} - {event.message}")
        
        # Write to event log file if enabled
        if self.event_log_enabled and hasattr(self, 'event_log_file'):
            with open(self.event_log_file, 'a') as f:
                f.write(json.dumps(event.dict()) + '\n')
        
        return event
    
    def get_events(
        self,
        event_type: Optional[str] = None,
        component: Optional[str] = None,
        job_id: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> List[Event]:
        """
        Get events matching the specified filters.
        
        Args:
            event_type: Optional event type filter
            component: Optional component filter
            job_id: Optional job ID filter
            start_time: Optional start time filter
            end_time: Optional end time filter
        
        Returns:
            List[Event]: Filtered events
        """
        filtered_events = self.events
        
        if event_type:
            filtered_events = [e for e in filtered_events if e.event_type == event_type]
        
        if component:
            filtered_events = [e for e in filtered_events if e.component == component]
        
        if job_id:
            filtered_events = [e for e in filtered_events if e.job_id == job_id]
        
        if start_time:
            start_str = start_time.isoformat()
            filtered_events = [e for e in filtered_events if e.timestamp >= start_str]
        
        if end_time:
            end_str = end_time.isoformat()
            filtered_events = [e for e in filtered_events if e.timestamp <= end_str]
        
        return filtered_events
    
    def time_execution(self, component: str, job_id: Optional[str] = None) -> Callable:
        """
        Decorator to time the execution of a function and record events.
        
        Args:
            component: Component name
            job_id: Optional job ID
        
        Returns:
            Callable: Decorator function
        """
        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                # Extract job_id from kwargs if available and not provided
                current_job_id = job_id
                if not current_job_id and 'job_id' in kwargs:
                    current_job_id = kwargs['job_id']
                
                # Record start event
                start_event = self.record_event(
                    event_type=EventType.AGENT_START,
                    component=component,
                    message=f"Starting {func.__name__}",
                    job_id=current_job_id,
                    data={"function": func.__name__}
                )
                
                start_time = time.time()
                
                try:
                    # Execute the function
                    result = func(*args, **kwargs)
                    
                    # Calculate duration
                    duration = time.time() - start_time
                    
                    # Record completion event
                    self.record_event(
                        event_type=EventType.AGENT_COMPLETE,
                        component=component,
                        message=f"Completed {func.__name__} in {duration:.2f}s",
                        job_id=current_job_id,
                        data={
                            "function": func.__name__,
                            "duration_seconds": duration
                        },
                        parent_event_id=start_event.id
                    )
                    
                    return result
                    
                except Exception as e:
                    # Calculate duration
                    duration = time.time() - start_time
                    
                    # Record error event
                    self.record_event(
                        event_type=EventType.AGENT_ERROR,
                        component=component,
                        message=f"Error in {func.__name__}: {str(e)}",
                        job_id=current_job_id,
                        data={
                            "function": func.__name__,
                            "duration_seconds": duration,
                            "error": str(e),
                            "traceback": traceback.format_exc()
                        },
                        parent_event_id=start_event.id
                    )
                    
                    # Re-raise the exception
                    raise
                    
            return wrapper
        return decorator
    
    def track_api_call(self, component: str, api_name: str, job_id: Optional[str] = None) -> Callable:
        """
        Decorator to track API calls and record events.
        
        Args:
            component: Component name
            api_name: Name of the API being called
            job_id: Optional job ID
        
        Returns:
            Callable: Decorator function
        """
        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                # Extract job_id from kwargs if available and not provided
                current_job_id = job_id
                if not current_job_id and 'job_id' in kwargs:
                    current_job_id = kwargs['job_id']
                
                # Record API call start event
                start_event = self.record_event(
                    event_type=EventType.API_CALL_START,
                    component=component,
                    message=f"Starting API call to {api_name}",
                    job_id=current_job_id,
                    data={
                        "api": api_name,
                        "function": func.__name__
                    }
                )
                
                start_time = time.time()
                
                try:
                    # Execute the function
                    result = func(*args, **kwargs)
                    
                    # Calculate duration
                    duration = time.time() - start_time
                    
                    # Record API call completion event
                    self.record_event(
                        event_type=EventType.API_CALL_COMPLETE,
                        component=component,
                        message=f"Completed API call to {api_name} in {duration:.2f}s",
                        job_id=current_job_id,
                        data={
                            "api": api_name,
                            "function": func.__name__,
                            "duration_seconds": duration
                        },
                        parent_event_id=start_event.id
                    )
                    
                    return result
                    
                except Exception as e:
                    # Calculate duration
                    duration = time.time() - start_time
                    
                    # Record API call error event
                    self.record_event(
                        event_type=EventType.API_CALL_ERROR,
                        component=component,
                        message=f"Error in API call to {api_name}: {str(e)}",
                        job_id=current_job_id,
                        data={
                            "api": api_name,
                            "function": func.__name__,
                            "duration_seconds": duration,
                            "error": str(e),
                            "traceback": traceback.format_exc()
                        },
                        parent_event_id=start_event.id
                    )
                    
                    # Re-raise the exception
                    raise
                    
            return wrapper
        return decorator


# Create a global observer instance
observer = PipelineObserver()


def get_observer() -> PipelineObserver:
    """
    Get the global observer instance.
    
    Returns:
        PipelineObserver: The global observer instance
    """
    return observer


def configure_observer(
    log_level: int = logging.INFO,
    log_to_console: bool = True,
    log_to_file: bool = True,
    log_dir: Optional[Path] = None,
    event_log_enabled: bool = True
) -> PipelineObserver:
    """
    Configure the global observer instance.
    
    Args:
        log_level: Logging level (default: INFO)
        log_to_console: Whether to log to console
        log_to_file: Whether to log to file
        log_dir: Directory for log files (default: ./logs)
        event_log_enabled: Whether to record events to JSONL file
    
    Returns:
        PipelineObserver: The configured observer instance
    """
    global observer
    observer = PipelineObserver(
        log_level=log_level,
        log_to_console=log_to_console,
        log_to_file=log_to_file,
        log_dir=log_dir,
        event_log_enabled=event_log_enabled
    )
    return observer
