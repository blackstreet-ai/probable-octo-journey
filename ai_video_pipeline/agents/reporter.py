"""
Reporter Agent module.

This module implements the Reporter Agent, which sends notifications and reports
about the video generation process to communication platforms like Slack.
"""

import os
import logging
import json
import requests
from typing import Dict, Any, Optional, List, Union
from pathlib import Path
from datetime import datetime
from pydantic import BaseModel, Field, validator

logger = logging.getLogger(__name__)


class SlackWebhookConfig(BaseModel):
    """Model for Slack webhook configuration."""
    webhook_url: str
    channel: Optional[str] = None
    username: str = "AI Video Pipeline"
    icon_emoji: str = ":movie_camera:"

    @validator('webhook_url')
    def validate_webhook_url(cls, v):
        """Validate that the webhook URL is properly formatted."""
        if not v.startswith('https://hooks.slack.com/services/'):
            raise ValueError("Invalid Slack webhook URL format")
        return v


class ReportMetrics(BaseModel):
    """Model for report metrics."""
    job_id: str
    status: str
    start_time: str
    end_time: str
    duration_seconds: float
    video_url: Optional[str] = None
    thumbnail_url: Optional[str] = None
    asset_counts: Dict[str, int] = Field(default_factory=dict)
    quality_issues: List[Dict[str, Any]] = Field(default_factory=list)
    compliance_issues: List[Dict[str, Any]] = Field(default_factory=list)


class ReporterAgent:
    """
    Reporter Agent responsible for sending notifications and reports
    about the video generation process to communication platforms.
    
    This agent handles:
    1. Generating summary reports of the video generation process
    2. Sending notifications to Slack via webhooks
    3. Formatting reports for different platforms
    4. Tracking key metrics about the generation process
    """
    
    def __init__(self, slack_config_path: Optional[Path] = None):
        """
        Initialize the Reporter Agent.
        
        Args:
            slack_config_path: Path to the Slack webhook configuration file.
                              If None, will look for SLACK_WEBHOOK_URL env var.
        """
        self.slack_config_path = slack_config_path
        self.slack_config = None
    
    def _load_slack_config(self) -> SlackWebhookConfig:
        """
        Load Slack webhook configuration from file or environment variable.
        
        Returns:
            SlackWebhookConfig: The loaded configuration
        
        Raises:
            ValueError: If configuration cannot be loaded
        """
        if self.slack_config_path and self.slack_config_path.exists():
            with open(self.slack_config_path, 'r') as f:
                config_data = json.load(f)
                return SlackWebhookConfig(**config_data)
        
        # Try from environment variable
        webhook_url = os.environ.get('SLACK_WEBHOOK_URL')
        if webhook_url:
            channel = os.environ.get('SLACK_CHANNEL')
            username = os.environ.get('SLACK_USERNAME', 'AI Video Pipeline')
            icon_emoji = os.environ.get('SLACK_ICON_EMOJI', ':movie_camera:')
            
            return SlackWebhookConfig(
                webhook_url=webhook_url,
                channel=channel,
                username=username,
                icon_emoji=icon_emoji
            )
        
        raise ValueError(
            "Slack webhook configuration not found. Provide a config file path or "
            "set the SLACK_WEBHOOK_URL environment variable."
        )
    
    def _extract_metrics(self, workflow_results: Dict[str, Any]) -> ReportMetrics:
        """
        Extract metrics from workflow results for reporting.
        
        Args:
            workflow_results: Results from the Executive Agent workflow
        
        Returns:
            ReportMetrics: Extracted metrics
        """
        # Extract basic information
        job_id = workflow_results.get('job_id', 'unknown')
        status = workflow_results.get('status', 'unknown')
        
        # Extract timestamps
        start_time = workflow_results.get('start_time', datetime.now().isoformat())
        end_time = workflow_results.get('end_time', datetime.now().isoformat())
        
        # Calculate duration
        try:
            start_dt = datetime.fromisoformat(start_time)
            end_dt = datetime.fromisoformat(end_time)
            duration_seconds = (end_dt - start_dt).total_seconds()
        except (ValueError, TypeError):
            duration_seconds = 0
        
        # Extract video URL from publishing results
        video_url = None
        if 'stages' in workflow_results and 'publishing' in workflow_results['stages']:
            publishing = workflow_results['stages']['publishing']
            if publishing.get('status') == 'success':
                video_url = publishing.get('upload_result', {}).get('video_url')
        
        # Extract thumbnail URL
        thumbnail_url = None
        if 'stages' in workflow_results and 'thumbnail' in workflow_results['stages']:
            thumbnail = workflow_results['stages']['thumbnail']
            if thumbnail.get('status') == 'success':
                thumbnail_path = thumbnail.get('thumbnail_path')
                if thumbnail_path:
                    # This is a local path, not a URL
                    # In a real system, this would be uploaded and a URL returned
                    thumbnail_url = f"file://{thumbnail_path}"
        
        # Count assets by type
        asset_counts = {}
        if 'assets' in workflow_results:
            for asset_type, assets in workflow_results['assets'].items():
                asset_counts[asset_type] = len(assets)
        
        # Extract quality issues
        quality_issues = []
        if 'stages' in workflow_results and 'motion_qc' in workflow_results['stages']:
            motion_qc = workflow_results['stages']['motion_qc']
            if motion_qc.get('status') == 'fail':
                for check_name, check in motion_qc.get('checks', {}).items():
                    if check.get('status') == 'fail':
                        quality_issues.append({
                            'type': check_name,
                            'message': check.get('message', f"Failed {check_name} check")
                        })
        
        # Extract compliance issues
        compliance_issues = []
        if 'stages' in workflow_results and 'compliance_qa' in workflow_results['stages']:
            compliance_qa = workflow_results['stages']['compliance_qa']
            compliance_issues = compliance_qa.get('issues', [])
        
        return ReportMetrics(
            job_id=job_id,
            status=status,
            start_time=start_time,
            end_time=end_time,
            duration_seconds=duration_seconds,
            video_url=video_url,
            thumbnail_url=thumbnail_url,
            asset_counts=asset_counts,
            quality_issues=quality_issues,
            compliance_issues=compliance_issues
        )
    
    def _format_slack_message(self, metrics: ReportMetrics) -> Dict[str, Any]:
        """
        Format metrics into a Slack message.
        
        Args:
            metrics: Report metrics
        
        Returns:
            Dict[str, Any]: Formatted Slack message
        """
        # Determine status emoji
        status_emoji = {
            'completed': ':white_check_mark:',
            'needs_review': ':warning:',
            'failed': ':x:',
        }.get(metrics.status, ':question:')
        
        # Format duration
        minutes, seconds = divmod(int(metrics.duration_seconds), 60)
        hours, minutes = divmod(minutes, 60)
        duration_str = f"{hours}h {minutes}m {seconds}s" if hours else f"{minutes}m {seconds}s"
        
        # Create message blocks
        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"Video Generation Report: {metrics.job_id}"
                }
            },
            {
                "type": "section",
                "fields": [
                    {
                        "type": "mrkdwn",
                        "text": f"*Status:* {status_emoji} {metrics.status.capitalize()}"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Duration:* {duration_str}"
                    }
                ]
            }
        ]
        
        # Add asset counts
        if metrics.asset_counts:
            asset_text = "*Assets:*\n" + "\n".join([
                f"• {asset_type}: {count}" 
                for asset_type, count in metrics.asset_counts.items()
            ])
            
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": asset_text
                }
            })
        
        # Add video link if available
        if metrics.video_url:
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Video URL:* <{metrics.video_url}|Watch on YouTube>"
                }
            })
        
        # Add thumbnail if available
        if metrics.thumbnail_url:
            blocks.append({
                "type": "image",
                "title": {
                    "type": "plain_text",
                    "text": "Video Thumbnail"
                },
                "image_url": metrics.thumbnail_url,
                "alt_text": "Video Thumbnail"
            })
        
        # Add issues if present
        if metrics.quality_issues or metrics.compliance_issues:
            issues_text = "*Issues Requiring Attention:*\n"
            
            for issue in metrics.quality_issues:
                issues_text += f"• Quality: {issue.get('message')}\n"
            
            for issue in metrics.compliance_issues:
                issues_text += f"• Compliance: {issue.get('message')}\n"
            
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": issues_text
                }
            })
        
        # Add footer
        blocks.append({
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": f"Generated at {metrics.end_time} • AI Video Automation Pipeline"
                }
            ]
        })
        
        # Create the full message
        return {
            "blocks": blocks,
            "text": f"Video Generation Report: {metrics.job_id} - {metrics.status.capitalize()}"
        }
    
    def _send_slack_notification(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """
        Send a notification to Slack.
        
        Args:
            message: Formatted Slack message
        
        Returns:
            Dict[str, Any]: Response from the Slack API
        """
        if not self.slack_config:
            self.slack_config = self._load_slack_config()
        
        payload = {
            "text": message.get("text", "Video Generation Report"),
            "blocks": message.get("blocks", []),
            "username": self.slack_config.username,
            "icon_emoji": self.slack_config.icon_emoji
        }
        
        if self.slack_config.channel:
            payload["channel"] = self.slack_config.channel
        
        try:
            response = requests.post(
                self.slack_config.webhook_url,
                json=payload,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200 and response.text == "ok":
                logger.info("Slack notification sent successfully")
                return {"status": "success", "message": "Notification sent successfully"}
            else:
                logger.error(f"Failed to send Slack notification: {response.status_code} - {response.text}")
                return {
                    "status": "error",
                    "message": f"Failed to send notification: {response.status_code}",
                    "response": response.text
                }
                
        except Exception as e:
            logger.error(f"Error sending Slack notification: {e}")
            return {"status": "error", "message": f"Error sending notification: {str(e)}"}
    
    def run(
        self, 
        workflow_results: Dict[str, Any],
        output_path: Optional[Path] = None,
        send_slack: bool = True
    ) -> Dict[str, Any]:
        """
        Run the Reporter Agent to generate and send reports.
        
        Args:
            workflow_results: Results from the Executive Agent workflow
            output_path: Optional path to save the report
            send_slack: Whether to send a Slack notification
        
        Returns:
            Dict[str, Any]: Reporting results
        """
        # Extract metrics from workflow results
        metrics = self._extract_metrics(workflow_results)
        
        # Generate report
        report = {
            "timestamp": datetime.now().isoformat(),
            "metrics": metrics.dict(),
            "notifications": []
        }
        
        # Send Slack notification if requested
        if send_slack:
            try:
                slack_message = self._format_slack_message(metrics)
                slack_result = self._send_slack_notification(slack_message)
                
                report["notifications"].append({
                    "platform": "slack",
                    "status": slack_result.get("status"),
                    "message": slack_result.get("message"),
                    "timestamp": datetime.now().isoformat()
                })
                
            except Exception as e:
                logger.error(f"Failed to send Slack notification: {e}")
                report["notifications"].append({
                    "platform": "slack",
                    "status": "error",
                    "message": f"Failed to send notification: {str(e)}",
                    "timestamp": datetime.now().isoformat()
                })
        
        # Save the report if output path is provided
        if output_path:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, 'w') as f:
                json.dump(report, f, indent=2)
            logger.info(f"Report saved to {output_path}")
        
        return report
