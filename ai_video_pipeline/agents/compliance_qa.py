"""
Compliance QA Agent module.

This module implements the Compliance QA Agent, which performs policy checks
for copyrighted imagery and TTS consent verification.
"""

from typing import Dict, List, Any, Optional, Union
import os
import logging
import json
from pathlib import Path
import re
from datetime import datetime

from ai_video_pipeline.config.settings import settings

logger = logging.getLogger(__name__)


class CompliancePolicy:
    """Base class for compliance policies."""
    
    def __init__(self, name: str, description: str):
        """
        Initialize a compliance policy.
        
        Args:
            name: Name of the policy
            description: Description of what the policy checks
        """
        self.name = name
        self.description = description
    
    def check(self, asset: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Check if an asset complies with the policy.
        
        Args:
            asset: Asset data to check
            context: Additional context for the check
            
        Returns:
            Dict[str, Any]: Check result with status and details
        """
        raise NotImplementedError("Subclasses must implement this method")


class CopyrightImageryPolicy(CompliancePolicy):
    """Policy for checking potential copyright issues in imagery."""
    
    def __init__(self):
        """Initialize the copyright imagery policy."""
        super().__init__(
            name="copyright_imagery",
            description="Checks for potential copyright issues in generated imagery"
        )
        # List of terms that might indicate copyrighted content
        self.copyright_terms = [
            "disney", "marvel", "star wars", "warner bros", "dc comics",
            "harry potter", "nintendo", "pokemon", "mickey", "batman",
            "superman", "spiderman", "avengers", "pixar", "dreamworks"
        ]
        # List of terms that might indicate trademarked logos
        self.trademark_terms = [
            "logo", "brand", "trademark", "corporate", "company logo"
        ]
    
    def check(self, asset: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Check if an image or video asset might contain copyrighted content.
        
        Args:
            asset: Asset data to check
            context: Additional context for the check
            
        Returns:
            Dict[str, Any]: Check result with status and details
        """
        result = {
            "policy": self.name,
            "status": "pass",
            "details": []
        }
        
        # Skip if not an image or video
        asset_type = asset.get("type", "")
        if asset_type not in ["image", "video"]:
            return result
        
        # Check prompt for copyright terms
        prompt = asset.get("metadata", {}).get("prompt", "").lower()
        if not prompt:
            result["status"] = "warning"
            result["details"].append({
                "type": "missing_data",
                "message": "No prompt data available to check for copyright issues"
            })
            return result
        
        # Check for copyright terms in prompt
        copyright_matches = []
        for term in self.copyright_terms:
            if term.lower() in prompt:
                copyright_matches.append(term)
        
        # Check for trademark terms in prompt
        trademark_matches = []
        for term in self.trademark_terms:
            if term.lower() in prompt:
                trademark_matches.append(term)
        
        # Determine result based on matches
        if copyright_matches:
            result["status"] = "fail"
            result["details"].append({
                "type": "copyright_term",
                "message": f"Prompt contains potential copyrighted terms: {', '.join(copyright_matches)}",
                "terms": copyright_matches
            })
        
        if trademark_matches:
            result["status"] = "warning"
            result["details"].append({
                "type": "trademark_term",
                "message": f"Prompt contains potential trademark terms: {', '.join(trademark_matches)}",
                "terms": trademark_matches
            })
        
        return result


class TTSConsentPolicy(CompliancePolicy):
    """Policy for checking TTS consent verification."""
    
    def __init__(self):
        """Initialize the TTS consent policy."""
        super().__init__(
            name="tts_consent",
            description="Verifies proper consent for text-to-speech voice synthesis"
        )
        # List of terms that might indicate a real person's voice
        self.celebrity_voice_terms = [
            "sounds like", "voice of", "celebrity", "famous", "impersonation",
            "imitate", "mimic", "clone voice"
        ]
    
    def check(self, asset: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Check if an audio asset has proper TTS consent.
        
        Args:
            asset: Asset data to check
            context: Additional context for the check
            
        Returns:
            Dict[str, Any]: Check result with status and details
        """
        result = {
            "policy": self.name,
            "status": "pass",
            "details": []
        }
        
        # Skip if not an audio asset
        asset_type = asset.get("type", "")
        if asset_type != "audio":
            return result
        
        # Check if this is a TTS asset
        metadata = asset.get("metadata", {})
        is_tts = metadata.get("type") == "voiceover" or "text_content" in metadata
        
        if not is_tts:
            # Not a TTS asset, so policy doesn't apply
            return result
        
        # Check for voice model information
        voice_model = metadata.get("voice_model", "")
        voice_provider = metadata.get("voice_provider", "")
        
        if not voice_model:
            result["status"] = "warning"
            result["details"].append({
                "type": "missing_data",
                "message": "No voice model information available to verify TTS consent"
            })
            return result
        
        # Check for terms that might indicate celebrity voice cloning
        voice_description = f"{voice_model} {voice_provider} {metadata.get('voice_description', '')}".lower()
        celebrity_matches = []
        for term in self.celebrity_voice_terms:
            if term.lower() in voice_description:
                celebrity_matches.append(term)
        
        # Check for consent documentation
        has_consent_doc = metadata.get("consent_documentation", False)
        
        # Determine result based on checks
        if celebrity_matches and not has_consent_doc:
            result["status"] = "fail"
            result["details"].append({
                "type": "celebrity_voice",
                "message": (
                    f"Voice description contains terms suggesting celebrity voice cloning: "
                    f"{', '.join(celebrity_matches)}, but no consent documentation is provided"
                ),
                "terms": celebrity_matches
            })
        elif celebrity_matches and has_consent_doc:
            result["status"] = "warning"
            result["details"].append({
                "type": "celebrity_voice_with_consent",
                "message": (
                    f"Voice description contains terms suggesting celebrity voice cloning: "
                    f"{', '.join(celebrity_matches)}, but consent documentation is provided"
                ),
                "terms": celebrity_matches
            })
        
        return result


class ComplianceQAAgent:
    """
    Compliance QA Agent for performing policy checks on assets.
    
    This agent is responsible for:
    1. Checking for potential copyright issues in imagery
    2. Verifying proper consent for TTS voice synthesis
    3. Ensuring compliance with other policy requirements
    """
    
    def __init__(self):
        """Initialize the Compliance QA Agent."""
        self.policies = [
            CopyrightImageryPolicy(),
            TTSConsentPolicy()
        ]
    
    def run(
        self,
        asset_manifest: Dict[str, Any],
        output_path: Optional[Path] = None
    ) -> Dict[str, Any]:
        """
        Run the Compliance QA Agent to check assets against policies.
        
        Args:
            asset_manifest: Asset manifest with assets to check
            output_path: Optional path to save the compliance report
            
        Returns:
            Dict[str, Any]: Compliance report with issues found
        """
        logger.info("Running Compliance QA Agent")
        
        # Initialize compliance report
        compliance_report = {
            "timestamp": datetime.now().isoformat(),
            "job_id": asset_manifest.get("job_id", "unknown"),
            "status": "pass",  # Default to pass, will be changed if issues found
            "issues": [],
            "warnings": [],
            "asset_checks": {}
        }
        
        # Check if there are assets to analyze
        if "assets" not in asset_manifest:
            compliance_report["status"] = "warning"
            compliance_report["warnings"].append("No assets found in manifest")
            return compliance_report
        
        # Process each asset type
        asset_types = ["images", "videos", "audio"]
        for asset_type in asset_types:
            if asset_type not in asset_manifest["assets"]:
                continue
                
            for asset in asset_manifest["assets"][asset_type]:
                asset_id = asset.get("id", "unknown")
                
                # Initialize asset check results
                asset_check = {
                    "asset_id": asset_id,
                    "asset_type": asset_type[:-1],  # Remove 's' to get singular form
                    "policy_checks": {}
                }
                
                # Apply each policy to the asset
                for policy in self.policies:
                    try:
                        # Run policy check
                        check_result = policy.check(asset, {"asset_manifest": asset_manifest})
                        
                        # Add check result to asset checks
                        asset_check["policy_checks"][policy.name] = check_result
                        
                        # Add to global issues or warnings if needed
                        if check_result["status"] == "fail":
                            compliance_report["issues"].append({
                                "asset_id": asset_id,
                                "policy": policy.name,
                                "details": check_result["details"]
                            })
                        elif check_result["status"] == "warning":
                            compliance_report["warnings"].append({
                                "asset_id": asset_id,
                                "policy": policy.name,
                                "details": check_result["details"]
                            })
                    except Exception as e:
                        logger.error(f"Error applying policy {policy.name} to asset {asset_id}: {str(e)}")
                        asset_check["policy_checks"][policy.name] = {
                            "policy": policy.name,
                            "status": "error",
                            "message": f"Error applying policy: {str(e)}"
                        }
                
                # Determine overall status for this asset
                asset_status = "pass"
                for policy_name, check_result in asset_check["policy_checks"].items():
                    if check_result["status"] == "fail":
                        asset_status = "fail"
                    elif check_result["status"] == "warning" and asset_status != "fail":
                        asset_status = "warning"
                
                asset_check["status"] = asset_status
                
                # Add asset check results to report
                compliance_report["asset_checks"][asset_id] = asset_check
        
        # Determine overall compliance status
        if len(compliance_report["issues"]) > 0:
            compliance_report["status"] = "fail"
        elif len(compliance_report["warnings"]) > 0:
            compliance_report["status"] = "warning"
        
        # Save report if output path is provided
        if output_path:
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            with open(output_path, "w") as f:
                json.dump(compliance_report, f, indent=2)
            logger.info(f"Compliance report saved to {output_path}")
        
        return compliance_report
