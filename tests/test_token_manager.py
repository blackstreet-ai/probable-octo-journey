#!/usr/bin/env python
"""
Unit tests for the TokenManager.

This module contains tests for the TokenManager class, which is responsible
for API key validation, rotation, and rate limiting for external services.
"""

import os
import time
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock, mock_open
from datetime import datetime, timedelta

from tools.token_manager import TokenManager


class TestTokenManager:
    """Tests for the TokenManager class."""

    @pytest.fixture
    def token_manager(self):
        """Create a TokenManager instance for testing."""
        return TokenManager()

    @pytest.fixture
    def sample_tokens(self):
        """Create sample tokens for testing."""
        return {
            "openai": {
                "current": "sk-openai-test-token-1",
                "backup": ["sk-openai-test-token-2", "sk-openai-test-token-3"],
                "last_validated": (datetime.now() - timedelta(hours=1)).isoformat(),
                "rate_limits": {
                    "requests_per_minute": 60,
                    "tokens_per_minute": 10000
                },
                "usage": {
                    "requests": 0,
                    "tokens": 0,
                    "reset_time": (datetime.now() + timedelta(minutes=1)).isoformat()
                }
            },
            "elevenlabs": {
                "current": "eleven-test-token-1",
                "backup": ["eleven-test-token-2"],
                "last_validated": (datetime.now() - timedelta(days=1)).isoformat(),
                "rate_limits": {
                    "requests_per_day": 100,
                    "characters_per_month": 10000
                },
                "usage": {
                    "requests": 0,
                    "characters": 0,
                    "reset_time": (datetime.now() + timedelta(days=1)).isoformat()
                }
            }
        }

    def test_init(self, token_manager):
        """Test the initialization of TokenManager."""
        assert token_manager is not None
        assert token_manager.tokens == {}
        assert token_manager.config_path is None

    @patch('os.environ.get')
    def test_load_tokens_from_env(self, mock_environ_get, token_manager):
        """Test loading tokens from environment variables."""
        # Mock environment variables
        mock_environ_get.side_effect = lambda key, default=None: {
            'OPENAI_API_KEY': 'sk-openai-env-token',
            'ELEVENLABS_API_KEY': 'eleven-env-token'
        }.get(key, default)
        
        # Call the method
        token_manager._load_tokens()
        
        # Check the result
        assert 'openai' in token_manager.tokens
        assert 'elevenlabs' in token_manager.tokens
        assert token_manager.tokens['openai']['current'] == 'sk-openai-env-token'
        assert token_manager.tokens['elevenlabs']['current'] == 'eleven-env-token'
        
        # Verify environment variables were checked
        mock_environ_get.assert_any_call('OPENAI_API_KEY')
        mock_environ_get.assert_any_call('ELEVENLABS_API_KEY')

    @patch('builtins.open', new_callable=mock_open)
    @patch('json.load')
    def test_load_tokens_from_file(self, mock_json_load, mock_file_open, token_manager, sample_tokens):
        """Test loading tokens from file."""
        # Set a config path
        token_manager.config_path = '/path/to/tokens.json'
        
        # Mock the JSON data
        mock_json_load.return_value = sample_tokens
        
        # Mock Path.exists to return True
        with patch.object(Path, 'exists', return_value=True):
            # Call the method
            token_manager._load_tokens()
        
        # Check the result
        assert token_manager.tokens == sample_tokens
        
        # Verify file was opened
        mock_file_open.assert_called_once_with('/path/to/tokens.json', 'r')
        mock_json_load.assert_called_once()

    @patch('builtins.open', new_callable=mock_open)
    @patch('json.dump')
    def test_save_tokens(self, mock_json_dump, mock_file_open, token_manager, sample_tokens):
        """Test saving tokens to file."""
        # Set a config path and tokens
        token_manager.config_path = '/path/to/tokens.json'
        token_manager.tokens = sample_tokens
        
        # Mock Path.parent.mkdir
        with patch.object(Path, 'parent', MagicMock()):
            # Call the method
            token_manager._save_tokens()
        
        # Verify file was opened and JSON was dumped
        mock_file_open.assert_called_once_with('/path/to/tokens.json', 'w')
        mock_json_dump.assert_called_once_with(sample_tokens, mock_file_open(), indent=2)

    def test_get_token(self, token_manager, sample_tokens):
        """Test getting a token for a service."""
        # Set tokens
        token_manager.tokens = sample_tokens
        
        # Call the method
        token = token_manager.get_token('openai')
        
        # Check the result
        assert token == 'sk-openai-test-token-1'
        
        # Test with non-existent service
        with pytest.raises(ValueError) as excinfo:
            token_manager.get_token('non_existent_service')
        assert "No token available for service" in str(excinfo.value)

    @patch('tools.token_manager.TokenManager._validate_openai_token')
    def test_validate_token_openai(self, mock_validate_openai, token_manager, sample_tokens):
        """Test validating an OpenAI token."""
        # Set tokens
        token_manager.tokens = sample_tokens
        
        # Mock validation result
        mock_validate_openai.return_value = True
        
        # Call the method
        result = token_manager.validate_token('openai')
        
        # Check the result
        assert result is True
        mock_validate_openai.assert_called_once_with('sk-openai-test-token-1')
        
        # Check that last_validated was updated
        assert 'last_validated' in token_manager.tokens['openai']
        
    @patch('tools.token_manager.TokenManager._validate_elevenlabs_token')
    def test_validate_token_elevenlabs(self, mock_validate_elevenlabs, token_manager, sample_tokens):
        """Test validating an ElevenLabs token."""
        # Set tokens
        token_manager.tokens = sample_tokens
        
        # Mock validation result
        mock_validate_elevenlabs.return_value = True
        
        # Call the method
        result = token_manager.validate_token('elevenlabs')
        
        # Check the result
        assert result is True
        mock_validate_elevenlabs.assert_called_once_with('eleven-test-token-1')
        
        # Check that last_validated was updated
        assert 'last_validated' in token_manager.tokens['elevenlabs']

    @patch('tools.token_manager.TokenManager._validate_openai_token')
    @patch('tools.token_manager.TokenManager._save_tokens')
    def test_rotate_token(self, mock_save_tokens, mock_validate_openai, token_manager, sample_tokens):
        """Test rotating a token when validation fails."""
        # Set tokens
        token_manager.tokens = sample_tokens
        
        # Mock validation to fail for current token but succeed for backup
        mock_validate_openai.side_effect = [False, True]
        
        # Call the method
        result = token_manager.validate_token('openai')
        
        # Check the result
        assert result is True
        assert token_manager.tokens['openai']['current'] == 'sk-openai-test-token-2'
        assert token_manager.tokens['openai']['backup'] == ['sk-openai-test-token-3', 'sk-openai-test-token-1']
        
        # Verify save was called
        mock_save_tokens.assert_called_once()

    @patch('tools.token_manager.TokenManager._validate_openai_token')
    def test_all_tokens_invalid(self, mock_validate_openai, token_manager, sample_tokens):
        """Test behavior when all tokens are invalid."""
        # Set tokens
        token_manager.tokens = sample_tokens
        
        # Mock validation to fail for all tokens
        mock_validate_openai.return_value = False
        
        # Call the method
        result = token_manager.validate_token('openai')
        
        # Check the result
        assert result is False
        assert mock_validate_openai.call_count == 3  # Current + 2 backups

    @patch('requests.get')
    def test_validate_openai_token_valid(self, mock_get, token_manager):
        """Test validating a valid OpenAI token."""
        # Mock response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response
        
        # Call the method
        result = token_manager._validate_openai_token('sk-test-token')
        
        # Check the result
        assert result is True
        mock_get.assert_called_once_with(
            'https://api.openai.com/v1/models',
            headers={'Authorization': 'Bearer sk-test-token'}
        )

    @patch('requests.get')
    def test_validate_openai_token_invalid(self, mock_get, token_manager):
        """Test validating an invalid OpenAI token."""
        # Mock response
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_get.return_value = mock_response
        
        # Call the method
        result = token_manager._validate_openai_token('sk-test-token')
        
        # Check the result
        assert result is False
        mock_get.assert_called_once()

    @patch('requests.get')
    def test_validate_elevenlabs_token_valid(self, mock_get, token_manager):
        """Test validating a valid ElevenLabs token."""
        # Mock response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'subscription': {'status': 'active'}}
        mock_get.return_value = mock_response
        
        # Call the method
        result = token_manager._validate_elevenlabs_token('eleven-test-token')
        
        # Check the result
        assert result is True
        mock_get.assert_called_once_with(
            'https://api.elevenlabs.io/v1/user/subscription',
            headers={'xi-api-key': 'eleven-test-token'}
        )

    @patch('requests.get')
    def test_validate_elevenlabs_token_invalid(self, mock_get, token_manager):
        """Test validating an invalid ElevenLabs token."""
        # Mock response
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_get.return_value = mock_response
        
        # Call the method
        result = token_manager._validate_elevenlabs_token('eleven-test-token')
        
        # Check the result
        assert result is False
        mock_get.assert_called_once()

    def test_track_usage_openai(self, token_manager, sample_tokens):
        """Test tracking usage for OpenAI."""
        # Set tokens
        token_manager.tokens = sample_tokens
        
        # Initial values
        initial_requests = token_manager.tokens['openai']['usage']['requests']
        initial_tokens = token_manager.tokens['openai']['usage']['tokens']
        
        # Call the method
        token_manager.track_usage('openai', requests=1, tokens=100)
        
        # Check the result
        assert token_manager.tokens['openai']['usage']['requests'] == initial_requests + 1
        assert token_manager.tokens['openai']['usage']['tokens'] == initial_tokens + 100

    def test_track_usage_elevenlabs(self, token_manager, sample_tokens):
        """Test tracking usage for ElevenLabs."""
        # Set tokens
        token_manager.tokens = sample_tokens
        
        # Initial values
        initial_requests = token_manager.tokens['elevenlabs']['usage']['requests']
        initial_characters = token_manager.tokens['elevenlabs']['usage']['characters']
        
        # Call the method
        token_manager.track_usage('elevenlabs', requests=1, characters=200)
        
        # Check the result
        assert token_manager.tokens['elevenlabs']['usage']['requests'] == initial_requests + 1
        assert token_manager.tokens['elevenlabs']['usage']['characters'] == initial_characters + 200

    def test_check_rate_limit_under_limit(self, token_manager, sample_tokens):
        """Test checking rate limit when under the limit."""
        # Set tokens with usage under limits
        token_manager.tokens = sample_tokens
        token_manager.tokens['openai']['usage']['requests'] = 30  # Under 60 per minute
        
        # Call the method
        result = token_manager.check_rate_limit('openai')
        
        # Check the result
        assert result is True

    def test_check_rate_limit_over_limit(self, token_manager, sample_tokens):
        """Test checking rate limit when over the limit."""
        # Set tokens with usage over limits
        token_manager.tokens = sample_tokens
        token_manager.tokens['openai']['usage']['requests'] = 70  # Over 60 per minute
        
        # Call the method
        result = token_manager.check_rate_limit('openai')
        
        # Check the result
        assert result is False

    @patch('time.sleep')
    def test_wait_for_rate_limit_reset(self, mock_sleep, token_manager, sample_tokens):
        """Test waiting for rate limit reset."""
        # Set tokens with reset time in the future
        token_manager.tokens = sample_tokens
        reset_time = datetime.now() + timedelta(seconds=5)
        token_manager.tokens['openai']['usage']['reset_time'] = reset_time.isoformat()
        
        # Call the method
        token_manager.wait_for_rate_limit_reset('openai')
        
        # Check that sleep was called with a positive duration
        mock_sleep.assert_called_once()
        sleep_duration = mock_sleep.call_args[0][0]
        assert sleep_duration > 0
        assert sleep_duration <= 5  # Should be less than or equal to 5 seconds

    @patch('tools.token_manager.TokenManager._load_tokens')
    @patch('tools.token_manager.TokenManager.validate_token')
    def test_get_valid_token(self, mock_validate, mock_load_tokens, token_manager, sample_tokens):
        """Test getting a valid token."""
        # Set tokens
        token_manager.tokens = sample_tokens
        
        # Mock validation to succeed
        mock_validate.return_value = True
        
        # Call the method
        token = token_manager.get_valid_token('openai')
        
        # Check the result
        assert token == 'sk-openai-test-token-1'
        mock_validate.assert_called_once_with('openai')

    @patch('tools.token_manager.TokenManager._load_tokens')
    @patch('tools.token_manager.TokenManager.validate_token')
    def test_get_valid_token_invalid(self, mock_validate, mock_load_tokens, token_manager, sample_tokens):
        """Test getting a valid token when all tokens are invalid."""
        # Set tokens
        token_manager.tokens = sample_tokens
        
        # Mock validation to fail
        mock_validate.return_value = False
        
        # Call the method and expect an exception
        with pytest.raises(ValueError) as excinfo:
            token_manager.get_valid_token('openai')
        
        # Check the exception message
        assert "No valid token available for service" in str(excinfo.value)
        mock_validate.assert_called_once_with('openai')

    @patch('tools.token_manager.TokenManager._load_tokens')
    @patch('tools.token_manager.TokenManager.check_rate_limit')
    @patch('tools.token_manager.TokenManager.wait_for_rate_limit_reset')
    def test_get_token_with_rate_limit(self, mock_wait, mock_check_limit, mock_load_tokens, token_manager, sample_tokens):
        """Test getting a token with rate limit check."""
        # Set tokens
        token_manager.tokens = sample_tokens
        
        # Mock rate limit check to first fail then succeed
        mock_check_limit.side_effect = [False, True]
        
        # Call the method
        token = token_manager.get_token_with_rate_limit('openai')
        
        # Check the result
        assert token == 'sk-openai-test-token-1'
        assert mock_check_limit.call_count == 2
        mock_wait.assert_called_once_with('openai')

    @patch('tools.token_manager.TokenManager._load_tokens')
    @patch('tools.token_manager.TokenManager.check_rate_limit')
    def test_get_token_with_rate_limit_under_limit(self, mock_check_limit, mock_load_tokens, token_manager, sample_tokens):
        """Test getting a token when under rate limit."""
        # Set tokens
        token_manager.tokens = sample_tokens
        
        # Mock rate limit check to succeed
        mock_check_limit.return_value = True
        
        # Call the method
        token = token_manager.get_token_with_rate_limit('openai')
        
        # Check the result
        assert token == 'sk-openai-test-token-1'
        mock_check_limit.assert_called_once_with('openai')

    @patch('tools.token_manager.TokenManager._load_tokens')
    def test_reset_usage(self, mock_load_tokens, token_manager, sample_tokens):
        """Test resetting usage statistics."""
        # Set tokens with some usage
        token_manager.tokens = sample_tokens
        token_manager.tokens['openai']['usage']['requests'] = 30
        token_manager.tokens['openai']['usage']['tokens'] = 5000
        
        # Call the method
        token_manager.reset_usage('openai')
        
        # Check the result
        assert token_manager.tokens['openai']['usage']['requests'] == 0
        assert token_manager.tokens['openai']['usage']['tokens'] == 0
        
        # Check that reset_time was updated to the future
        reset_time = datetime.fromisoformat(token_manager.tokens['openai']['usage']['reset_time'])
        assert reset_time > datetime.now()
