"""
Tests for the Observability module.

This module contains tests for the Observability module and related functionality.
"""

import os
import json
import pytest
import logging
from pathlib import Path
from unittest.mock import patch, MagicMock, mock_open, call
import time
from datetime import datetime

from ai_video_pipeline.tools.observability import (
    PipelineObserver,
    Event,
    EventType,
    get_observer,
    configure_observer
)


@pytest.fixture
def observer():
    """Create a PipelineObserver instance for testing."""
    # Create with log_to_file=False to avoid creating actual log files during tests
    return PipelineObserver(log_to_file=False, event_log_enabled=False)


class TestEvent:
    """Test suite for the Event model."""

    def test_init_defaults(self):
        """Test initialization with default values."""
        event = Event(
            event_type=EventType.AGENT_START,
            component="TestComponent",
            message="Test message"
        )
        
        assert event.event_type == EventType.AGENT_START
        assert event.component == "TestComponent"
        assert event.message == "Test message"
        assert event.job_id is None
        assert event.data == {}
        assert event.parent_event_id is None
        assert event.id is not None  # Should auto-generate UUID
        assert event.timestamp is not None  # Should auto-generate timestamp

    def test_init_custom(self):
        """Test initialization with custom values."""
        event = Event(
            id="test_id",
            timestamp="2025-05-04T12:00:00Z",
            event_type=EventType.AGENT_COMPLETE,
            component="TestComponent",
            message="Test message",
            job_id="test_job",
            data={"key": "value"},
            parent_event_id="parent_id"
        )
        
        assert event.id == "test_id"
        assert event.timestamp == "2025-05-04T12:00:00Z"
        assert event.event_type == EventType.AGENT_COMPLETE
        assert event.component == "TestComponent"
        assert event.message == "Test message"
        assert event.job_id == "test_job"
        assert event.data == {"key": "value"}
        assert event.parent_event_id == "parent_id"


class TestPipelineObserver:
    """Test suite for the PipelineObserver class."""

    def test_init_defaults(self):
        """Test initialization with default values."""
        observer = PipelineObserver(log_to_file=False, event_log_enabled=False)
        
        assert observer.log_level == logging.INFO
        assert observer.log_to_console is True
        assert observer.log_to_file is False
        assert observer.event_log_enabled is False
        assert observer.events == []
        assert observer.logger is not None

    @patch('logging.getLogger')
    @patch('logging.FileHandler')
    def test_setup_logging(self, mock_file_handler, mock_get_logger, tmp_path):
        """Test setting up logging configuration."""
        # Create a mock logger
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger
        
        # Create observer with log file
        log_dir = tmp_path / "logs"
        observer = PipelineObserver(
            log_level=logging.DEBUG,
            log_to_console=True,
            log_to_file=True,
            log_dir=log_dir,
            event_log_enabled=True
        )
        
        # Check that logger was configured
        assert mock_get_logger.called
        assert mock_file_handler.called
        
        # Verify log directory was created
        assert log_dir.exists()

    def test_record_event(self, observer):
        """Test recording an event."""
        # Record an event
        event = observer.record_event(
            event_type=EventType.AGENT_START,
            component="TestComponent",
            message="Test message",
            job_id="test_job",
            data={"key": "value"}
        )
        
        # Check the event
        assert event.event_type == EventType.AGENT_START
        assert event.component == "TestComponent"
        assert event.message == "Test message"
        assert event.job_id == "test_job"
        assert event.data == {"key": "value"}
        
        # Check that event was added to the list
        assert len(observer.events) == 1
        assert observer.events[0].id == event.id

    @patch('builtins.open', new_callable=mock_open)
    def test_record_event_to_file(self, mock_file_open, tmp_path):
        """Test recording an event to a file."""
        # Create observer with event log enabled
        log_dir = tmp_path / "logs"
        observer = PipelineObserver(
            log_to_file=False,  # Don't create actual log files
            log_dir=log_dir,
            event_log_enabled=True
        )
        
        # Set event log file path
        observer.event_log_file = log_dir / "test_events.jsonl"
        
        # Record an event
        event = observer.record_event(
            event_type=EventType.AGENT_START,
            component="TestComponent",
            message="Test message"
        )
        
        # Check that file was opened and written to
        mock_file_open.assert_called_once_with(observer.event_log_file, 'a')
        mock_file_open().write.assert_called_once()
        
        # Verify that the written data is valid JSON
        written_data = mock_file_open().write.call_args[0][0]
        event_dict = json.loads(written_data.rstrip())
        assert event_dict["event_type"] == EventType.AGENT_START
        assert event_dict["component"] == "TestComponent"
        assert event_dict["message"] == "Test message"

    def test_get_events_no_filter(self, observer):
        """Test getting events with no filter."""
        # Add some events
        observer.record_event(
            event_type=EventType.AGENT_START,
            component="Component1",
            message="Start 1",
            job_id="job1"
        )
        observer.record_event(
            event_type=EventType.AGENT_COMPLETE,
            component="Component1",
            message="Complete 1",
            job_id="job1"
        )
        observer.record_event(
            event_type=EventType.AGENT_START,
            component="Component2",
            message="Start 2",
            job_id="job2"
        )
        
        # Get all events
        events = observer.get_events()
        
        # Check the result
        assert len(events) == 3

    def test_get_events_with_filters(self, observer):
        """Test getting events with filters."""
        # Add some events
        observer.record_event(
            event_type=EventType.AGENT_START,
            component="Component1",
            message="Start 1",
            job_id="job1"
        )
        observer.record_event(
            event_type=EventType.AGENT_COMPLETE,
            component="Component1",
            message="Complete 1",
            job_id="job1"
        )
        observer.record_event(
            event_type=EventType.AGENT_START,
            component="Component2",
            message="Start 2",
            job_id="job2"
        )
        
        # Filter by event type
        events = observer.get_events(event_type=EventType.AGENT_START)
        assert len(events) == 2
        assert all(e.event_type == EventType.AGENT_START for e in events)
        
        # Filter by component
        events = observer.get_events(component="Component1")
        assert len(events) == 2
        assert all(e.component == "Component1" for e in events)
        
        # Filter by job ID
        events = observer.get_events(job_id="job2")
        assert len(events) == 1
        assert events[0].job_id == "job2"
        
        # Combined filters
        events = observer.get_events(
            event_type=EventType.AGENT_START,
            component="Component1"
        )
        assert len(events) == 1
        assert events[0].event_type == EventType.AGENT_START
        assert events[0].component == "Component1"

    def test_time_execution_decorator_success(self, observer):
        """Test time_execution decorator with successful function."""
        # Create a test function
        @observer.time_execution(component="TestComponent", job_id="test_job")
        def test_function():
            return "success"
        
        # Call the function
        result = test_function()
        
        # Check the result
        assert result == "success"
        
        # Check that events were recorded
        assert len(observer.events) == 2
        assert observer.events[0].event_type == EventType.AGENT_START
        assert observer.events[1].event_type == EventType.AGENT_COMPLETE
        assert observer.events[0].component == "TestComponent"
        assert observer.events[1].component == "TestComponent"
        assert observer.events[0].job_id == "test_job"
        assert observer.events[1].job_id == "test_job"
        assert observer.events[1].parent_event_id == observer.events[0].id

    def test_time_execution_decorator_error(self, observer):
        """Test time_execution decorator with function that raises an error."""
        # Create a test function that raises an error
        @observer.time_execution(component="TestComponent", job_id="test_job")
        def test_function_error():
            raise ValueError("Test error")
        
        # Call the function and expect an error
        with pytest.raises(ValueError, match="Test error"):
            test_function_error()
        
        # Check that events were recorded
        assert len(observer.events) == 2
        assert observer.events[0].event_type == EventType.AGENT_START
        assert observer.events[1].event_type == EventType.AGENT_ERROR
        assert "Test error" in observer.events[1].message
        assert "traceback" in observer.events[1].data

    def test_track_api_call_decorator_success(self, observer):
        """Test track_api_call decorator with successful function."""
        # Create a test function
        @observer.track_api_call(component="TestComponent", api_name="TestAPI", job_id="test_job")
        def test_api_call():
            return "api_result"
        
        # Call the function
        result = test_api_call()
        
        # Check the result
        assert result == "api_result"
        
        # Check that events were recorded
        assert len(observer.events) == 2
        assert observer.events[0].event_type == EventType.API_CALL_START
        assert observer.events[1].event_type == EventType.API_CALL_COMPLETE
        assert observer.events[0].component == "TestComponent"
        assert observer.events[1].component == "TestComponent"
        assert observer.events[0].job_id == "test_job"
        assert observer.events[1].job_id == "test_job"
        assert "TestAPI" in observer.events[0].message
        assert "TestAPI" in observer.events[1].message
        assert observer.events[1].parent_event_id == observer.events[0].id

    def test_track_api_call_decorator_error(self, observer):
        """Test track_api_call decorator with function that raises an error."""
        # Create a test function that raises an error
        @observer.track_api_call(component="TestComponent", api_name="TestAPI", job_id="test_job")
        def test_api_call_error():
            raise ConnectionError("API connection error")
        
        # Call the function and expect an error
        with pytest.raises(ConnectionError, match="API connection error"):
            test_api_call_error()
        
        # Check that events were recorded
        assert len(observer.events) == 2
        assert observer.events[0].event_type == EventType.API_CALL_START
        assert observer.events[1].event_type == EventType.API_CALL_ERROR
        assert "TestAPI" in observer.events[0].message
        assert "API connection error" in observer.events[1].message
        assert "traceback" in observer.events[1].data


class TestObserverGlobalFunctions:
    """Test suite for the global observer functions."""

    def test_get_observer(self):
        """Test getting the global observer instance."""
        observer = get_observer()
        assert isinstance(observer, PipelineObserver)

    def test_configure_observer(self):
        """Test configuring the global observer instance."""
        # Configure with custom settings
        observer = configure_observer(
            log_level=logging.DEBUG,
            log_to_console=False,
            log_to_file=False,
            event_log_enabled=False
        )
        
        # Check that settings were applied
        assert isinstance(observer, PipelineObserver)
        assert observer.log_level == logging.DEBUG
        assert observer.log_to_console is False
        assert observer.log_to_file is False
        assert observer.event_log_enabled is False
        
        # Get the observer again and verify it's the same instance
        observer2 = get_observer()
        assert observer is observer2
