"""
Retry and backoff utilities for API calls.

This module provides decorators and utilities for implementing retry logic
with exponential backoff for API calls to external services.
"""

import time
import random
import logging
import functools
from typing import Callable, Any, Optional, Type, List, Union, Dict, Tuple
import inspect

logger = logging.getLogger(__name__)


def retry_with_backoff(
    max_retries: int = 3,
    initial_backoff: float = 1.0,
    max_backoff: float = 60.0,
    backoff_factor: float = 2.0,
    jitter: bool = True,
    exceptions_to_retry: Optional[Union[Type[Exception], Tuple[Type[Exception], ...]]] = None,
    should_retry_fn: Optional[Callable[[Exception], bool]] = None,
    on_retry_callback: Optional[Callable[[int, Exception, float], None]] = None,
):
    """
    Decorator for retrying a function with exponential backoff when exceptions occur.
    
    Args:
        max_retries: Maximum number of retries before giving up
        initial_backoff: Initial backoff time in seconds
        max_backoff: Maximum backoff time in seconds
        backoff_factor: Multiplier for backoff time after each retry
        jitter: Whether to add randomness to backoff time
        exceptions_to_retry: Exception types to retry on (default: all exceptions)
        should_retry_fn: Function to determine if retry should occur based on exception
        on_retry_callback: Function to call before each retry
    
    Returns:
        Decorator function
    """
    exceptions_to_retry = exceptions_to_retry or Exception
    
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            retries = 0
            backoff = initial_backoff
            
            while True:
                try:
                    return func(*args, **kwargs)
                except exceptions_to_retry as e:
                    retries += 1
                    
                    # Check if we should retry based on the exception
                    if should_retry_fn and not should_retry_fn(e):
                        logger.warning(
                            f"Not retrying {func.__name__} due to exception: {str(e)}"
                        )
                        raise
                    
                    # Check if we've exceeded max retries
                    if retries > max_retries:
                        logger.error(
                            f"Max retries ({max_retries}) exceeded for {func.__name__}"
                        )
                        raise
                    
                    # Calculate backoff time with optional jitter
                    wait_time = min(backoff, max_backoff)
                    if jitter:
                        wait_time = wait_time * (0.5 + random.random())
                    
                    # Log retry attempt
                    logger.warning(
                        f"Retry {retries}/{max_retries} for {func.__name__} "
                        f"after {wait_time:.2f}s due to: {str(e)}"
                    )
                    
                    # Call the retry callback if provided
                    if on_retry_callback:
                        on_retry_callback(retries, e, wait_time)
                    
                    # Wait before retrying
                    time.sleep(wait_time)
                    
                    # Increase backoff for next retry
                    backoff = min(backoff * backoff_factor, max_backoff)
                    
        return wrapper
    
    return decorator


def fal_ai_retry(
    max_retries: int = 5,
    initial_backoff: float = 2.0,
    max_backoff: float = 60.0,
):
    """
    Specialized retry decorator for fal.ai API calls.
    
    Args:
        max_retries: Maximum number of retries before giving up
        initial_backoff: Initial backoff time in seconds
        max_backoff: Maximum backoff time in seconds
    
    Returns:
        Decorator function
    """
    # Define which exceptions should trigger a retry for fal.ai
    fal_ai_retry_exceptions = (
        # Common HTTP errors
        ConnectionError,
        TimeoutError,
        # Add specific fal.ai exceptions here when known
    )
    
    # Define a function to determine if an exception should trigger a retry
    def should_retry_fal_ai(exception):
        # Retry on connection errors, timeouts, and rate limits
        if isinstance(exception, (ConnectionError, TimeoutError)):
            return True
        
        # Check for rate limit or server errors in the exception message
        error_msg = str(exception).lower()
        if any(msg in error_msg for msg in ["rate limit", "429", "too many requests", "server error", "503"]):
            return True
        
        return False
    
    # Define a callback for logging fal.ai specific retry information
    def fal_ai_retry_callback(retry_count, exception, wait_time):
        logger.warning(
            f"fal.ai API call failed (attempt {retry_count}). "
            f"Retrying in {wait_time:.2f}s. Error: {str(exception)}"
        )
    
    # Return the configured retry decorator
    return retry_with_backoff(
        max_retries=max_retries,
        initial_backoff=initial_backoff,
        max_backoff=max_backoff,
        backoff_factor=2.0,
        jitter=True,
        exceptions_to_retry=fal_ai_retry_exceptions,
        should_retry_fn=should_retry_fal_ai,
        on_retry_callback=fal_ai_retry_callback
    )


def elevenlabs_retry(
    max_retries: int = 4,
    initial_backoff: float = 1.5,
    max_backoff: float = 45.0,
):
    """
    Specialized retry decorator for ElevenLabs API calls.
    
    Args:
        max_retries: Maximum number of retries before giving up
        initial_backoff: Initial backoff time in seconds
        max_backoff: Maximum backoff time in seconds
    
    Returns:
        Decorator function
    """
    # Define which exceptions should trigger a retry for ElevenLabs
    elevenlabs_retry_exceptions = (
        # Common HTTP errors
        ConnectionError,
        TimeoutError,
        # Add specific ElevenLabs exceptions here when known
    )
    
    # Define a function to determine if an exception should trigger a retry
    def should_retry_elevenlabs(exception):
        # Retry on connection errors, timeouts, and rate limits
        if isinstance(exception, (ConnectionError, TimeoutError)):
            return True
        
        # Check for rate limit or server errors in the exception message
        error_msg = str(exception).lower()
        if any(msg in error_msg for msg in ["rate limit", "429", "too many requests", "server error", "503"]):
            return True
        
        return False
    
    # Define a callback for logging ElevenLabs specific retry information
    def elevenlabs_retry_callback(retry_count, exception, wait_time):
        logger.warning(
            f"ElevenLabs API call failed (attempt {retry_count}). "
            f"Retrying in {wait_time:.2f}s. Error: {str(exception)}"
        )
    
    # Return the configured retry decorator
    return retry_with_backoff(
        max_retries=max_retries,
        initial_backoff=initial_backoff,
        max_backoff=max_backoff,
        backoff_factor=2.0,
        jitter=True,
        exceptions_to_retry=elevenlabs_retry_exceptions,
        should_retry_fn=should_retry_elevenlabs,
        on_retry_callback=elevenlabs_retry_callback
    )


class RetrySession:
    """
    A session class that wraps API clients with retry functionality.
    
    This class can be used to add retry functionality to any API client
    by wrapping its methods with the appropriate retry decorators.
    """
    
    def __init__(
        self,
        client,
        retry_decorator: Callable = None,
        methods_to_wrap: Optional[List[str]] = None
    ):
        """
        Initialize a RetrySession.
        
        Args:
            client: The API client to wrap
            retry_decorator: The retry decorator to apply to methods
            methods_to_wrap: List of method names to wrap with retry logic
                             If None, wraps all public methods
        """
        self.client = client
        self.retry_decorator = retry_decorator or retry_with_backoff()
        
        # If no methods specified, find all public methods
        if methods_to_wrap is None:
            methods_to_wrap = [
                name for name, method in inspect.getmembers(client, inspect.ismethod)
                if not name.startswith('_')
            ]
        
        # Wrap each method with the retry decorator
        for method_name in methods_to_wrap:
            if hasattr(client, method_name) and callable(getattr(client, method_name)):
                original_method = getattr(client, method_name)
                wrapped_method = self.retry_decorator(original_method)
                setattr(self, method_name, wrapped_method)
    
    def __getattr__(self, name):
        """
        Forward any other attribute access to the underlying client.
        
        Args:
            name: Attribute name
        
        Returns:
            The attribute from the underlying client
        """
        return getattr(self.client, name)
