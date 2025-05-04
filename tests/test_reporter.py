"""
Tests for the Reporter Agent.

This module contains tests for the Reporter Agent and related functionality.
"""

import os
import json
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock, mock_open
from datetime import datetime

from ai_video_pipeline.agents.reporter import (
    ReporterAgent,
    SlackWebhookConfig,
    ReportMetrics
)


@pytest.fixture
def sample_workflow_results():
    """Create sample workflow results for testing."""
    return {
        "job_id": "test_job_123",
        "status": "completed",
        "start_time": "2025-05-04T10:00:00Z",
        "end_time": "2025-05-04T10:30:00Z",
        "duration_seconds": 1800.0,
        "job_spec": {
            "title": "Test Video",
            "topic": "Testing the AI Video Pipeline",
            "tone": "informative",
            "runtime": 60,
            "target_platform": "YouTube"
        },
        "assets": {
            "images": [
                {"id": "image_1", "path": "/path/to/image1.png"},
                {"id": "image_2", "path": "/path/to/image2.png"}
            ],
            "videos": [
                {"id": "video_1", "path": "/path/to/video1.mp4"}
            ],
            "audio": [
                {"id": "audio_1", "path": "/path/to/audio1.wav"}
            ]
        },
        "stages": {
            "script": {"status": "success"},
            "prompts": {"status": "success"},
            "images": {"status": "success"},
            "videos": {"status": "success"},
            "voice": {"status": "success"},
            "music": {"status": "success"},
            "audio_mix": {"status": "success"},
            "timeline": {"status": "success"},
            "motion_qc": {
                "status": "pass",
                "checks": {
                    "duration": {"status": "pass"},
                    "aspect_ratio": {"status": "pass"},
                    "duplicate_frames": {"status": "pass"}
                }
            },
            "compliance_qa": {
                "status": "pass",
                "issues": [],
                "warnings": []
            },
            "thumbnail": {
                "status": "success",
                "thumbnail_path": "/path/to/thumbnail.png"
            },
            "publishing": {
                "status": "success",
                "upload_result": {
                    "video_id": "test_video_id",
                    "video_url": "https://www.youtube.com/watch?v=test_video_id"
                }
            }
        }
    }


@pytest.fixture
def sample_workflow_results_with_issues():
    """Create sample workflow results with issues for testing."""
    return {
        "job_id": "test_job_456",
        "status": "needs_review",
        "start_time": "2025-05-04T11:00:00Z",
        "end_time": "2025-05-04T11:30:00Z",
        "duration_seconds": 1800.0,
        "critical_issues": [
            "Motion QC failed: Video duration too short",
            "Compliance QA failed: Copyright terms found in image prompt"
        ],
        "assets": {
            "images": [
                {"id": "image_1", "path": "/path/to/image1.png"}
            ],
            "videos": [
                {"id": "video_1", "path": "/path/to/video1.mp4"}
            ]
        },
        "stages": {
            "motion_qc": {
                "status": "fail",
                "message": "Video quality issues detected",
                "checks": {
                    "duration": {
                        "status": "fail",
                        "message": "Video duration too short"
                    },
                    "aspect_ratio": {"status": "pass"},
                    "duplicate_frames": {"status": "pass"}
                }
            },
            "compliance_qa": {
                "status": "fail",
                "message": "Compliance issues detected",
                "issues": [
                    {"message": "Copyright terms found in image prompt"}
                ],
                "warnings": []
            },
            "thumbnail": {
                "status": "success",
                "thumbnail_path": "/path/to/thumbnail.png"
            },
            "publishing": {
                "status": "skipped",
                "message": "Publishing skipped due to critical issues"
            }
        }
    }


@pytest.fixture
def reporter_agent():
    """Create a ReporterAgent instance for testing."""
    return ReporterAgent()


class TestSlackWebhookConfig:
    """Test suite for the SlackWebhookConfig model."""

    def test_init_defaults(self):
        """Test initialization with default values."""
        config = SlackWebhookConfig(
            webhook_url="https://hooks.slack.com/services/T00000000/B00000000/XXXXXXXXXXXXXXXXXXXXXXXX"
        )
        
        assert config.webhook_url == "https://hooks.slack.com/services/T00000000/B00000000/XXXXXXXXXXXXXXXXXXXXXXXX"
        assert config.channel is None
        assert config.username == "AI Video Pipeline"
        assert config.icon_emoji == ":movie_camera:"

    def test_init_custom(self):
        """Test initialization with custom values."""
        config = SlackWebhookConfig(
            webhook_url="https://hooks.slack.com/services/T00000000/B00000000/XXXXXXXXXXXXXXXXXXXXXXXX",
            channel="#test-channel",
            username="Test Bot",
            icon_emoji=":robot_face:"
        )
        
        assert config.webhook_url == "https://hooks.slack.com/services/T00000000/B00000000/XXXXXXXXXXXXXXXXXXXXXXXX"
        assert config.channel == "#test-channel"
        assert config.username == "Test Bot"
        assert config.icon_emoji == ":robot_face:"

    def test_validate_webhook_url_valid(self):
        """Test webhook URL validation with valid URL."""
        config = SlackWebhookConfig(
            webhook_url="https://hooks.slack.com/services/T00000000/B00000000/XXXXXXXXXXXXXXXXXXXXXXXX"
        )
        assert config.webhook_url == "https://hooks.slack.com/services/T00000000/B00000000/XXXXXXXXXXXXXXXXXXXXXXXX"

    def test_validate_webhook_url_invalid(self):
        """Test webhook URL validation with invalid URL."""
        with pytest.raises(ValueError, match="Invalid Slack webhook URL format"):
            SlackWebhookConfig(webhook_url="https://example.com/webhook")


class TestReportMetrics:
    """Test suite for the ReportMetrics model."""

    def test_init_minimal(self):
        """Test initialization with minimal required fields."""
        metrics = ReportMetrics(
            job_id="test_job",
            status="completed",
            start_time="2025-05-04T10:00:00Z",
            end_time="2025-05-04T10:30:00Z",
            duration_seconds=1800.0
        )
        
        assert metrics.job_id == "test_job"
        assert metrics.status == "completed"
        assert metrics.start_time == "2025-05-04T10:00:00Z"
        assert metrics.end_time == "2025-05-04T10:30:00Z"
        assert metrics.duration_seconds == 1800.0
        assert metrics.video_url is None
        assert metrics.thumbnail_url is None
        assert metrics.asset_counts == {}
        assert metrics.quality_issues == []
        assert metrics.compliance_issues == []

    def test_init_full(self):
        """Test initialization with all fields."""
        metrics = ReportMetrics(
            job_id="test_job",
            status="completed",
            start_time="2025-05-04T10:00:00Z",
            end_time="2025-05-04T10:30:00Z",
            duration_seconds=1800.0,
            video_url="https://example.com/video",
            thumbnail_url="https://example.com/thumbnail",
            asset_counts={"images": 2, "videos": 1},
            quality_issues=[{"type": "duration", "message": "Too short"}],
            compliance_issues=[{"message": "Copyright issue"}]
        )
        
        assert metrics.job_id == "test_job"
        assert metrics.status == "completed"
        assert metrics.start_time == "2025-05-04T10:00:00Z"
        assert metrics.end_time == "2025-05-04T10:30:00Z"
        assert metrics.duration_seconds == 1800.0
        assert metrics.video_url == "https://example.com/video"
        assert metrics.thumbnail_url == "https://example.com/thumbnail"
        assert metrics.asset_counts == {"images": 2, "videos": 1}
        assert len(metrics.quality_issues) == 1
        assert metrics.quality_issues[0]["message"] == "Too short"
        assert len(metrics.compliance_issues) == 1
        assert metrics.compliance_issues[0]["message"] == "Copyright issue"


class TestReporterAgent:
    """Test suite for the ReporterAgent class."""

    def test_init(self, reporter_agent):
        """Test initialization of ReporterAgent."""
        assert reporter_agent is not None
        assert reporter_agent.slack_config_path is None
        assert reporter_agent.slack_config is None

    @patch('os.environ.get')
    def test_load_slack_config_from_env(self, mock_environ_get, reporter_agent):
        """Test loading Slack config from environment variables."""
        # Mock environment variables
        mock_environ_get.side_effect = lambda key, default=None: {
            'SLACK_WEBHOOK_URL': 'https://hooks.slack.com/services/T00000000/B00000000/XXXXXXXXXXXXXXXXXXXXXXXX',
            'SLACK_CHANNEL': '#test-channel',
            'SLACK_USERNAME': 'Test Bot',
            'SLACK_ICON_EMOJI': ':robot_face:'
        }.get(key, default)
        
        # Call the method
        config = reporter_agent._load_slack_config()
        
        # Check the result
        assert config.webhook_url == 'https://hooks.slack.com/services/T00000000/B00000000/XXXXXXXXXXXXXXXXXXXXXXXX'
        assert config.channel == '#test-channel'
        assert config.username == 'Test Bot'
        assert config.icon_emoji == ':robot_face:'
        
        # Verify environment variables were checked
        assert mock_environ_get.call_count >= 1
        mock_environ_get.assert_any_call('SLACK_WEBHOOK_URL')

    @patch('builtins.open', new_callable=mock_open)
    @patch('json.load')
    def test_load_slack_config_from_file(self, mock_json_load, mock_file_open, tmp_path):
        """Test loading Slack config from file."""
        # Create a config file path
        config_path = tmp_path / "slack_config.json"
        
        # Mock the JSON data
        mock_json_load.return_value = {
            "webhook_url": "https://hooks.slack.com/services/T00000000/B00000000/XXXXXXXXXXXXXXXXXXXXXXXX",
            "channel": "#file-channel",
            "username": "File Bot",
            "icon_emoji": ":file:"
        }
        
        # Create agent with config path
        agent = ReporterAgent(slack_config_path=config_path)
        
        # Mock Path.exists to return True
        with patch.object(Path, 'exists', return_value=True):
            # Call the method
            config = agent._load_slack_config()
        
        # Check the result
        assert config.webhook_url == 'https://hooks.slack.com/services/T00000000/B00000000/XXXXXXXXXXXXXXXXXXXXXXXX'
        assert config.channel == '#file-channel'
        assert config.username == 'File Bot'
        assert config.icon_emoji == ':file:'
        
        # Verify file was opened
        mock_file_open.assert_called_once_with(config_path, 'r')
        mock_json_load.assert_called_once()

    @patch('os.environ.get')
    def test_load_slack_config_error(self, mock_environ_get, reporter_agent):
        """Test error when Slack config is not available."""
        # Mock environment variable to return None
        mock_environ_get.return_value = None
        
        # Call the method and check for error
        with pytest.raises(ValueError, match="Slack webhook configuration not found"):
            reporter_agent._load_slack_config()

    def test_extract_metrics_success(self, reporter_agent, sample_workflow_results):
        """Test extracting metrics from successful workflow results."""
        # Call the method
        metrics = reporter_agent._extract_metrics(sample_workflow_results)
        
        # Check the result
        assert metrics.job_id == "test_job_123"
        assert metrics.status == "completed"
        assert metrics.start_time == "2025-05-04T10:00:00Z"
        assert metrics.end_time == "2025-05-04T10:30:00Z"
        assert metrics.duration_seconds == 1800.0
        assert metrics.video_url == "https://www.youtube.com/watch?v=test_video_id"
        assert metrics.thumbnail_url == "file:///path/to/thumbnail.png"
        assert metrics.asset_counts == {"images": 2, "videos": 1, "audio": 1}
        assert len(metrics.quality_issues) == 0
        assert len(metrics.compliance_issues) == 0

    def test_extract_metrics_with_issues(self, reporter_agent, sample_workflow_results_with_issues):
        """Test extracting metrics from workflow results with issues."""
        # Call the method
        metrics = reporter_agent._extract_metrics(sample_workflow_results_with_issues)
        
        # Check the result
        assert metrics.job_id == "test_job_456"
        assert metrics.status == "needs_review"
        assert metrics.start_time == "2025-05-04T11:00:00Z"
        assert metrics.end_time == "2025-05-04T11:30:00Z"
        assert metrics.duration_seconds == 1800.0
        assert metrics.video_url is None  # No video URL due to skipped publishing
        assert metrics.thumbnail_url == "file:///path/to/thumbnail.png"
        assert metrics.asset_counts == {"images": 1, "videos": 1}
        
        # Check quality issues
        assert len(metrics.quality_issues) == 1
        assert metrics.quality_issues[0]["type"] == "duration"
        assert metrics.quality_issues[0]["message"] == "Video duration too short"
        
        # Check compliance issues
        assert len(metrics.compliance_issues) == 1
        assert metrics.compliance_issues[0]["message"] == "Copyright terms found in image prompt"

    def test_format_slack_message_success(self, reporter_agent):
        """Test formatting Slack message for successful workflow."""
        # Create test metrics
        metrics = ReportMetrics(
            job_id="test_job_123",
            status="completed",
            start_time="2025-05-04T10:00:00Z",
            end_time="2025-05-04T10:30:00Z",
            duration_seconds=1800.0,
            video_url="https://www.youtube.com/watch?v=test_video_id",
            thumbnail_url="https://example.com/thumbnail.png",
            asset_counts={"images": 2, "videos": 1, "audio": 1}
        )
        
        # Call the method
        message = reporter_agent._format_slack_message(metrics)
        
        # Check the result
        assert "blocks" in message
        assert isinstance(message["blocks"], list)
        assert len(message["blocks"]) > 0
        
        # Check header
        assert message["blocks"][0]["type"] == "header"
        assert "test_job_123" in message["blocks"][0]["text"]["text"]
        
        # Check status section
        assert ":white_check_mark: Completed" in message["blocks"][1]["fields"][0]["text"]
        
        # Check video URL
        video_block = next((b for b in message["blocks"] if "Video URL" in b.get("text", {}).get("text", "")), None)
        assert video_block is not None
        assert "https://www.youtube.com/watch?v=test_video_id" in video_block["text"]["text"]
        
        # Check thumbnail
        thumbnail_block = next((b for b in message["blocks"] if b.get("type") == "image"), None)
        assert thumbnail_block is not None
        assert thumbnail_block["image_url"] == "https://example.com/thumbnail.png"

    def test_format_slack_message_with_issues(self, reporter_agent):
        """Test formatting Slack message for workflow with issues."""
        # Create test metrics with issues
        metrics = ReportMetrics(
            job_id="test_job_456",
            status="needs_review",
            start_time="2025-05-04T11:00:00Z",
            end_time="2025-05-04T11:30:00Z",
            duration_seconds=1800.0,
            asset_counts={"images": 1, "videos": 1},
            quality_issues=[{"type": "duration", "message": "Video duration too short"}],
            compliance_issues=[{"message": "Copyright terms found in image prompt"}]
        )
        
        # Call the method
        message = reporter_agent._format_slack_message(metrics)
        
        # Check the result
        assert "blocks" in message
        
        # Check status section
        assert ":warning: Needs_review" in message["blocks"][1]["fields"][0]["text"]
        
        # Check issues section
        issues_block = next((b for b in message["blocks"] if "Issues Requiring Attention" in b.get("text", {}).get("text", "")), None)
        assert issues_block is not None
        assert "Quality: Video duration too short" in issues_block["text"]["text"]
        assert "Compliance: Copyright terms found in image prompt" in issues_block["text"]["text"]

    @patch('ai_video_pipeline.agents.reporter.ReporterAgent._load_slack_config')
    @patch('requests.post')
    def test_send_slack_notification_success(self, mock_post, mock_load_config, reporter_agent):
        """Test sending Slack notification successfully."""
        # Mock config
        mock_load_config.return_value = SlackWebhookConfig(
            webhook_url="https://hooks.slack.com/services/T00000000/B00000000/XXXXXXXXXXXXXXXXXXXXXXXX",
            channel="#test-channel",
            username="Test Bot",
            icon_emoji=":robot_face:"
        )
        
        # Mock response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "ok"
        mock_post.return_value = mock_response
        
        # Create test message
        message = {
            "text": "Test message",
            "blocks": [{"type": "section", "text": {"type": "mrkdwn", "text": "Test content"}}]
        }
        
        # Call the method
        result = reporter_agent._send_slack_notification(message)
        
        # Check the result
        assert result["status"] == "success"
        assert "Notification sent successfully" in result["message"]
        
        # Verify requests.post was called correctly
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        assert args[0] == "https://hooks.slack.com/services/T00000000/B00000000/XXXXXXXXXXXXXXXXXXXXXXXX"
        assert "json" in kwargs
        assert kwargs["json"]["text"] == "Test message"
        assert kwargs["json"]["blocks"] == message["blocks"]
        assert kwargs["json"]["username"] == "Test Bot"
        assert kwargs["json"]["icon_emoji"] == ":robot_face:"
        assert kwargs["json"]["channel"] == "#test-channel"

    @patch('ai_video_pipeline.agents.reporter.ReporterAgent._load_slack_config')
    @patch('requests.post')
    def test_send_slack_notification_error(self, mock_post, mock_load_config, reporter_agent):
        """Test sending Slack notification with error."""
        # Mock config
        mock_load_config.return_value = SlackWebhookConfig(
            webhook_url="https://hooks.slack.com/services/T00000000/B00000000/XXXXXXXXXXXXXXXXXXXXXXXX"
        )
        
        # Mock response with error
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.text = "invalid_payload"
        mock_post.return_value = mock_response
        
        # Create test message
        message = {"text": "Test message"}
        
        # Call the method
        result = reporter_agent._send_slack_notification(message)
        
        # Check the result
        assert result["status"] == "error"
        assert "Failed to send notification" in result["message"]
        assert result["response"] == "invalid_payload"

    @patch('ai_video_pipeline.agents.reporter.ReporterAgent._extract_metrics')
    @patch('ai_video_pipeline.agents.reporter.ReporterAgent._format_slack_message')
    @patch('ai_video_pipeline.agents.reporter.ReporterAgent._send_slack_notification')
    @patch('builtins.open', new_callable=mock_open)
    @patch('json.dump')
    def test_run_with_slack(self, mock_json_dump, mock_file_open, mock_send_notification, 
                           mock_format_message, mock_extract_metrics, reporter_agent, 
                           sample_workflow_results, tmp_path):
        """Test run method with Slack notification."""
        # Mock extracted metrics
        mock_metrics = MagicMock()
        mock_extract_metrics.return_value = mock_metrics
        
        # Mock formatted message
        mock_message = {"text": "Test message"}
        mock_format_message.return_value = mock_message
        
        # Mock notification result
        mock_send_notification.return_value = {
            "status": "success",
            "message": "Notification sent successfully"
        }
        
        # Create output path
        output_path = tmp_path / "report.json"
        
        # Call the method
        result = reporter_agent.run(
            workflow_results=sample_workflow_results,
            output_path=output_path,
            send_slack=True
        )
        
        # Check the result
        assert "timestamp" in result
        assert "metrics" in result
        assert "notifications" in result
        assert len(result["notifications"]) == 1
        assert result["notifications"][0]["platform"] == "slack"
        assert result["notifications"][0]["status"] == "success"
        
        # Verify method calls
        mock_extract_metrics.assert_called_once_with(sample_workflow_results)
        mock_format_message.assert_called_once_with(mock_metrics)
        mock_send_notification.assert_called_once_with(mock_message)
        mock_file_open.assert_called_once_with(output_path, 'w')
        mock_json_dump.assert_called_once()

    @patch('ai_video_pipeline.agents.reporter.ReporterAgent._extract_metrics')
    def test_run_without_slack(self, mock_extract_metrics, reporter_agent, sample_workflow_results):
        """Test run method without Slack notification."""
        # Mock extracted metrics
        mock_metrics = MagicMock()
        mock_extract_metrics.return_value = mock_metrics
        
        # Call the method
        result = reporter_agent.run(
            workflow_results=sample_workflow_results,
            send_slack=False
        )
        
        # Check the result
        assert "timestamp" in result
        assert "metrics" in result
        assert "notifications" in result
        assert len(result["notifications"]) == 0
        
        # Verify method calls
        mock_extract_metrics.assert_called_once_with(sample_workflow_results)
