#!/usr/bin/env python
"""
Token manager for API key validation and rotation.

This module provides functions for validating, rotating, and managing API keys
for various external services used by the AI Video Automation Pipeline.
"""

import json
import logging
import os
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple, Union

import requests

# Configure logging
logger = logging.getLogger(__name__)

class TokenManager:
    """
    Manager for API key validation and rotation.
    
    This class provides methods for validating, rotating, and managing API keys
    for various external services used by the AI Video Automation Pipeline.
    """
    
    def __init__(self, token_file: Optional[str] = None):
        """
        Initialize the TokenManager.
        
        Args:
            token_file: Path to the token file (optional)
        """
        # Default token file path
        if token_file is None:
            token_file = str(Path(__file__).parent.parent / "configs" / "tokens.json")
        
        self.token_file = token_file
        self.tokens = self._load_tokens()
        
        # Rate limiting settings
        self.rate_limits = {
            "openai": {"requests_per_minute": 60, "requests_per_day": 10000},
            "elevenlabs": {"requests_per_minute": 30, "requests_per_day": 5000},
            "fal_ai": {"requests_per_minute": 20, "requests_per_day": 2000},
            "youtube": {"requests_per_minute": 10, "requests_per_day": 1000}
        }
        
        # Request tracking
        self.request_history = {}
    
    def _load_tokens(self) -> Dict[str, Any]:
        """
        Load tokens from the token file.
        
        Returns:
            Dict[str, Any]: Loaded tokens
        """
        try:
            # Check if token file exists
            if not os.path.exists(self.token_file):
                # Create default token structure
                tokens = {
                    "openai": {
                        "api_key": os.environ.get("OPENAI_API_KEY", ""),
                        "last_validated": None,
                        "valid": False,
                        "expires": None
                    },
                    "elevenlabs": {
                        "api_key": os.environ.get("ELEVENLABS_API_KEY", ""),
                        "last_validated": None,
                        "valid": False,
                        "expires": None
                    },
                    "fal_ai": {
                        "key": os.environ.get("FAL_AI_KEY", ""),
                        "secret": os.environ.get("FAL_AI_SECRET", ""),
                        "last_validated": None,
                        "valid": False,
                        "expires": None
                    },
                    "youtube": {
                        "client_secrets_file": os.environ.get("YOUTUBE_CLIENT_SECRETS_FILE", ""),
                        "credentials_file": os.environ.get("YOUTUBE_CREDENTIALS_FILE", ""),
                        "last_validated": None,
                        "valid": False,
                        "expires": None
                    },
                    "slack": {
                        "webhook_url": os.environ.get("SLACK_WEBHOOK_URL", ""),
                        "last_validated": None,
                        "valid": False,
                        "expires": None
                    }
                }
                
                # Save default tokens
                self._save_tokens(tokens)
                return tokens
            
            # Load tokens from file
            with open(self.token_file, "r") as f:
                tokens = json.load(f)
            
            # Update tokens with environment variables if available
            if "openai" in tokens and os.environ.get("OPENAI_API_KEY"):
                tokens["openai"]["api_key"] = os.environ.get("OPENAI_API_KEY")
            
            if "elevenlabs" in tokens and os.environ.get("ELEVENLABS_API_KEY"):
                tokens["elevenlabs"]["api_key"] = os.environ.get("ELEVENLABS_API_KEY")
            
            if "fal_ai" in tokens:
                if os.environ.get("FAL_AI_KEY"):
                    tokens["fal_ai"]["key"] = os.environ.get("FAL_AI_KEY")
                if os.environ.get("FAL_AI_SECRET"):
                    tokens["fal_ai"]["secret"] = os.environ.get("FAL_AI_SECRET")
            
            if "youtube" in tokens:
                if os.environ.get("YOUTUBE_CLIENT_SECRETS_FILE"):
                    tokens["youtube"]["client_secrets_file"] = os.environ.get("YOUTUBE_CLIENT_SECRETS_FILE")
                if os.environ.get("YOUTUBE_CREDENTIALS_FILE"):
                    tokens["youtube"]["credentials_file"] = os.environ.get("YOUTUBE_CREDENTIALS_FILE")
            
            if "slack" in tokens and os.environ.get("SLACK_WEBHOOK_URL"):
                tokens["slack"]["webhook_url"] = os.environ.get("SLACK_WEBHOOK_URL")
            
            return tokens
            
        except Exception as e:
            logger.error(f"Failed to load tokens: {str(e)}")
            return {}
    
    def _save_tokens(self, tokens: Dict[str, Any]) -> None:
        """
        Save tokens to the token file.
        
        Args:
            tokens: Tokens to save
        """
        try:
            # Ensure directory exists
            os.makedirs(os.path.dirname(self.token_file), exist_ok=True)
            
            # Save tokens to file
            with open(self.token_file, "w") as f:
                json.dump(tokens, f, indent=2)
            
        except Exception as e:
            logger.error(f"Failed to save tokens: {str(e)}")
    
    def validate_token(self, service: str) -> bool:
        """
        Validate a token for a service.
        
        Args:
            service: Service name
            
        Returns:
            bool: True if the token is valid, False otherwise
        """
        try:
            # Check if service is supported
            if service not in self.tokens:
                logger.error(f"Unsupported service: {service}")
                return False
            
            # Get token data
            token_data = self.tokens[service]
            
            # Check if token was recently validated
            if token_data.get("last_validated") is not None:
                last_validated = datetime.fromisoformat(token_data["last_validated"])
                if datetime.now() - last_validated < timedelta(hours=1) and token_data.get("valid", False):
                    logger.debug(f"Token for {service} was recently validated")
                    return True
            
            # Validate token based on service
            if service == "openai":
                valid = self._validate_openai_token(token_data["api_key"])
            elif service == "elevenlabs":
                valid = self._validate_elevenlabs_token(token_data["api_key"])
            elif service == "fal_ai":
                valid = self._validate_fal_ai_token(token_data["key"], token_data["secret"])
            elif service == "youtube":
                valid = self._validate_youtube_token(
                    token_data["client_secrets_file"],
                    token_data["credentials_file"]
                )
            elif service == "slack":
                valid = self._validate_slack_token(token_data["webhook_url"])
            else:
                logger.error(f"Validation not implemented for service: {service}")
                return False
            
            # Update token data
            token_data["last_validated"] = datetime.now().isoformat()
            token_data["valid"] = valid
            
            # Save updated tokens
            self._save_tokens(self.tokens)
            
            return valid
            
        except Exception as e:
            logger.error(f"Failed to validate token for {service}: {str(e)}")
            return False
    
    def _validate_openai_token(self, api_key: str) -> bool:
        """
        Validate an OpenAI API key.
        
        Args:
            api_key: OpenAI API key
            
        Returns:
            bool: True if the API key is valid, False otherwise
        """
        try:
            # Check if API key is empty
            if not api_key:
                logger.error("OpenAI API key is empty")
                return False
            
            # Make a simple API request to validate the key
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
            
            response = requests.get(
                "https://api.openai.com/v1/models",
                headers=headers
            )
            
            # Check if the request was successful
            if response.status_code == 200:
                logger.info("OpenAI API key is valid")
                return True
            else:
                logger.error(f"OpenAI API key validation failed: {response.status_code} {response.text}")
                return False
            
        except Exception as e:
            logger.error(f"Failed to validate OpenAI API key: {str(e)}")
            return False
    
    def _validate_elevenlabs_token(self, api_key: str) -> bool:
        """
        Validate an ElevenLabs API key.
        
        Args:
            api_key: ElevenLabs API key
            
        Returns:
            bool: True if the API key is valid, False otherwise
        """
        try:
            # Check if API key is empty
            if not api_key:
                logger.error("ElevenLabs API key is empty")
                return False
            
            # Make a simple API request to validate the key
            headers = {
                "xi-api-key": api_key,
                "Content-Type": "application/json"
            }
            
            response = requests.get(
                "https://api.elevenlabs.io/v1/voices",
                headers=headers
            )
            
            # Check if the request was successful
            if response.status_code == 200:
                logger.info("ElevenLabs API key is valid")
                return True
            else:
                logger.error(f"ElevenLabs API key validation failed: {response.status_code} {response.text}")
                return False
            
        except Exception as e:
            logger.error(f"Failed to validate ElevenLabs API key: {str(e)}")
            return False
    
    def _validate_fal_ai_token(self, key: str, secret: str) -> bool:
        """
        Validate fal.ai API credentials.
        
        Args:
            key: fal.ai API key
            secret: fal.ai API secret
            
        Returns:
            bool: True if the API credentials are valid, False otherwise
        """
        try:
            # Check if API credentials are empty
            if not key or not secret:
                logger.error("fal.ai API credentials are incomplete")
                return False
            
            # For fal.ai, we'll just check if the credentials are not empty
            # as there's no simple validation endpoint
            logger.info("fal.ai API credentials are present (not fully validated)")
            return True
            
        except Exception as e:
            logger.error(f"Failed to validate fal.ai API credentials: {str(e)}")
            return False
    
    def _validate_youtube_token(self, client_secrets_file: str, credentials_file: str) -> bool:
        """
        Validate YouTube API credentials.
        
        Args:
            client_secrets_file: Path to the client secrets file
            credentials_file: Path to the credentials file
            
        Returns:
            bool: True if the API credentials are valid, False otherwise
        """
        try:
            # Check if API credentials files exist
            if not client_secrets_file or not os.path.exists(client_secrets_file):
                logger.error("YouTube client secrets file not found")
                return False
            
            # For YouTube, we'll just check if the client secrets file exists
            # as validating the credentials would require a more complex OAuth flow
            logger.info("YouTube API credentials file exists (not fully validated)")
            return True
            
        except Exception as e:
            logger.error(f"Failed to validate YouTube API credentials: {str(e)}")
            return False
    
    def _validate_slack_token(self, webhook_url: str) -> bool:
        """
        Validate a Slack webhook URL.
        
        Args:
            webhook_url: Slack webhook URL
            
        Returns:
            bool: True if the webhook URL is valid, False otherwise
        """
        try:
            # Check if webhook URL is empty
            if not webhook_url:
                logger.error("Slack webhook URL is empty")
                return False
            
            # Check if the webhook URL has the expected format
            if not webhook_url.startswith("https://hooks.slack.com/services/"):
                logger.error("Slack webhook URL has invalid format")
                return False
            
            # For Slack, we'll just check the URL format
            # as testing the webhook would send a message
            logger.info("Slack webhook URL has valid format (not fully validated)")
            return True
            
        except Exception as e:
            logger.error(f"Failed to validate Slack webhook URL: {str(e)}")
            return False
    
    def get_token(self, service: str) -> Union[str, Dict[str, str], None]:
        """
        Get a token for a service.
        
        Args:
            service: Service name
            
        Returns:
            Union[str, Dict[str, str], None]: Token or token data for the service
        """
        try:
            # Check if service is supported
            if service not in self.tokens:
                logger.error(f"Unsupported service: {service}")
                return None
            
            # Get token data
            token_data = self.tokens[service]
            
            # Validate token if not recently validated
            if not token_data.get("valid", False):
                if not self.validate_token(service):
                    logger.error(f"Token for {service} is invalid")
                    return None
            
            # Return token based on service
            if service == "openai":
                return token_data["api_key"]
            elif service == "elevenlabs":
                return token_data["api_key"]
            elif service == "fal_ai":
                return {"key": token_data["key"], "secret": token_data["secret"]}
            elif service == "youtube":
                return {
                    "client_secrets_file": token_data["client_secrets_file"],
                    "credentials_file": token_data["credentials_file"]
                }
            elif service == "slack":
                return token_data["webhook_url"]
            else:
                logger.error(f"Token retrieval not implemented for service: {service}")
                return None
            
        except Exception as e:
            logger.error(f"Failed to get token for {service}: {str(e)}")
            return None
    
    def rotate_token(self, service: str) -> bool:
        """
        Rotate a token for a service.
        
        Args:
            service: Service name
            
        Returns:
            bool: True if the token was rotated, False otherwise
        """
        try:
            # Check if service is supported
            if service not in self.tokens:
                logger.error(f"Unsupported service: {service}")
                return False
            
            # Get token data
            token_data = self.tokens[service]
            
            # Token rotation is not implemented for most services
            # as it would require integration with service-specific rotation mechanisms
            logger.warning(f"Token rotation not implemented for service: {service}")
            
            # Mark token as invalid to force re-validation
            token_data["valid"] = False
            token_data["last_validated"] = None
            
            # Save updated tokens
            self._save_tokens(self.tokens)
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to rotate token for {service}: {str(e)}")
            return False
    
    def check_rate_limit(self, service: str) -> bool:
        """
        Check if a service is rate limited.
        
        Args:
            service: Service name
            
        Returns:
            bool: True if the service is not rate limited, False otherwise
        """
        try:
            # Check if service is supported
            if service not in self.rate_limits:
                logger.error(f"Rate limits not defined for service: {service}")
                return True  # Allow by default
            
            # Get rate limits
            limits = self.rate_limits[service]
            
            # Initialize request history for service if not exists
            if service not in self.request_history:
                self.request_history[service] = {
                    "minute": {"count": 0, "reset_time": time.time() + 60},
                    "day": {"count": 0, "reset_time": time.time() + 86400}
                }
            
            # Get request history
            history = self.request_history[service]
            
            # Check and reset minute counter if needed
            if time.time() >= history["minute"]["reset_time"]:
                history["minute"]["count"] = 0
                history["minute"]["reset_time"] = time.time() + 60
            
            # Check and reset day counter if needed
            if time.time() >= history["day"]["reset_time"]:
                history["day"]["count"] = 0
                history["day"]["reset_time"] = time.time() + 86400
            
            # Check if rate limits are exceeded
            if history["minute"]["count"] >= limits["requests_per_minute"]:
                logger.warning(f"Rate limit exceeded for {service}: {limits['requests_per_minute']} requests per minute")
                return False
            
            if history["day"]["count"] >= limits["requests_per_day"]:
                logger.warning(f"Rate limit exceeded for {service}: {limits['requests_per_day']} requests per day")
                return False
            
            # Increment counters
            history["minute"]["count"] += 1
            history["day"]["count"] += 1
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to check rate limit for {service}: {str(e)}")
            return True  # Allow by default in case of error
    
    def record_request(self, service: str) -> None:
        """
        Record a request to a service for rate limiting.
        
        Args:
            service: Service name
        """
        try:
            # Check if service is supported
            if service not in self.rate_limits:
                return
            
            # Check rate limit (this also records the request)
            self.check_rate_limit(service)
            
        except Exception as e:
            logger.error(f"Failed to record request for {service}: {str(e)}")
