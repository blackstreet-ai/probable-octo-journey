"""
Tests for the retry utilities.

This module contains tests for the retry utilities in the AI Video Pipeline.
"""

import time
import unittest
from unittest.mock import Mock, patch

import pytest

from ai_video_pipeline.utils.retry import (
    retry_with_backoff,
    fal_ai_retry,
    elevenlabs_retry,
    RetrySession
)


class TestRetryWithBackoff:
    """Tests for the retry_with_backoff decorator."""

    def test_successful_execution(self):
        """Test that a successful function is called only once."""
        mock_func = Mock(return_value="success")
        decorated = retry_with_backoff()(mock_func)
        
        result = decorated()
        
        assert result == "success"
        assert mock_func.call_count == 1
    
    def test_retry_on_exception(self):
        """Test that a function is retried when it raises an exception."""
        mock_func = Mock(side_effect=[ValueError("Error"), "success"])
        decorated = retry_with_backoff(max_retries=3)(mock_func)
        
        result = decorated()
        
        assert result == "success"
        assert mock_func.call_count == 2
    
    def test_max_retries_exceeded(self):
        """Test that an exception is raised when max retries is exceeded."""
        mock_func = Mock(side_effect=ValueError("Error"))
        decorated = retry_with_backoff(max_retries=2)(mock_func)
        
        with pytest.raises(ValueError):
            decorated()
        
        assert mock_func.call_count == 3  # Initial call + 2 retries
    
    def test_specific_exceptions(self):
        """Test that only specified exceptions trigger retries."""
        mock_func = Mock(side_effect=[ValueError("Error"), "success"])
        decorated = retry_with_backoff(
            max_retries=2,
            exceptions_to_retry=ValueError
        )(mock_func)
        
        result = decorated()
        
        assert result == "success"
        assert mock_func.call_count == 2
        
        # Test with an exception that should not be retried
        mock_func = Mock(side_effect=[TypeError("Error"), "success"])
        decorated = retry_with_backoff(
            max_retries=2,
            exceptions_to_retry=ValueError
        )(mock_func)
        
        with pytest.raises(TypeError):
            decorated()
        
        assert mock_func.call_count == 1  # No retries
    
    def test_should_retry_function(self):
        """Test that the should_retry_fn controls whether to retry."""
        should_retry = Mock(side_effect=[True, False])
        mock_func = Mock(side_effect=[ValueError("Error"), ValueError("Error"), "success"])
        
        decorated = retry_with_backoff(
            max_retries=3,
            should_retry_fn=should_retry
        )(mock_func)
        
        with pytest.raises(ValueError):
            decorated()
        
        assert mock_func.call_count == 2  # Initial call + 1 retry
        assert should_retry.call_count == 2
    
    def test_on_retry_callback(self):
        """Test that the on_retry_callback is called before each retry."""
        callback = Mock()
        mock_func = Mock(side_effect=[ValueError("Error"), ValueError("Error"), "success"])
        
        decorated = retry_with_backoff(
            max_retries=3,
            on_retry_callback=callback
        )(mock_func)
        
        result = decorated()
        
        assert result == "success"
        assert mock_func.call_count == 3  # Initial call + 2 retries
        assert callback.call_count == 2  # Called before each retry
    
    @patch('time.sleep')
    def test_backoff_timing(self, mock_sleep):
        """Test that the backoff timing increases with each retry."""
        mock_func = Mock(side_effect=[ValueError("Error"), ValueError("Error"), "success"])
        
        decorated = retry_with_backoff(
            max_retries=3,
            initial_backoff=1.0,
            backoff_factor=2.0,
            jitter=False
        )(mock_func)
        
        result = decorated()
        
        assert result == "success"
        assert mock_func.call_count == 3  # Initial call + 2 retries
        assert mock_sleep.call_count == 2  # Called before each retry
        
        # Check that the second sleep was longer than the first
        assert mock_sleep.call_args_list[1][0][0] > mock_sleep.call_args_list[0][0][0]


class TestSpecializedRetryDecorators:
    """Tests for the specialized retry decorators."""
    
    @patch('time.sleep')
    def test_fal_ai_retry(self, mock_sleep):
        """Test the fal_ai_retry decorator."""
        mock_func = Mock(side_effect=[ConnectionError("Network error"), "success"])
        
        decorated = fal_ai_retry()(mock_func)
        
        result = decorated()
        
        assert result == "success"
        assert mock_func.call_count == 2  # Initial call + 1 retry
        assert mock_sleep.call_count == 1  # Called before the retry
    
    @patch('time.sleep')
    def test_elevenlabs_retry(self, mock_sleep):
        """Test the elevenlabs_retry decorator."""
        mock_func = Mock(side_effect=[TimeoutError("Timeout"), "success"])
        
        decorated = elevenlabs_retry()(mock_func)
        
        result = decorated()
        
        assert result == "success"
        assert mock_func.call_count == 2  # Initial call + 1 retry
        assert mock_sleep.call_count == 1  # Called before the retry


class TestRetrySession:
    """Tests for the RetrySession class."""
    
    def test_method_wrapping(self):
        """Test that methods are wrapped with the retry decorator."""
        class TestClient:
            def method1(self):
                return "method1"
            
            def method2(self):
                return "method2"
            
            def _private_method(self):
                return "private"
        
        client = TestClient()
        retry_decorator = Mock(side_effect=lambda f: f)
        session = RetrySession(client, retry_decorator=retry_decorator)
        
        # Public methods should be wrapped
        assert session.method1() == "method1"
        assert session.method2() == "method2"
        
        # Private methods should not be wrapped but accessible
        assert session._private_method() == "private"
        
        # The decorator should have been called for each public method
        assert retry_decorator.call_count == 2
    
    def test_specific_methods(self):
        """Test that only specified methods are wrapped."""
        class TestClient:
            def method1(self):
                return "method1"
            
            def method2(self):
                return "method2"
        
        client = TestClient()
        retry_decorator = Mock(side_effect=lambda f: f)
        session = RetrySession(
            client,
            retry_decorator=retry_decorator,
            methods_to_wrap=["method1"]
        )
        
        # Only method1 should be wrapped
        assert session.method1() == "method1"
        assert session.method2() == "method2"
        
        # The decorator should have been called only for method1
        assert retry_decorator.call_count == 1
    
    def test_attribute_forwarding(self):
        """Test that attributes are forwarded to the underlying client."""
        class TestClient:
            attribute = "value"
        
        client = TestClient()
        session = RetrySession(client)
        
        # Attributes should be forwarded
        assert session.attribute == "value"


if __name__ == "__main__":
    pytest.main()
