"""
Motion QC Agent module.

This module implements the Motion QC Agent, which performs heuristic checks
on video clips for quality control, including duration, aspect ratio, and
duplicate frame detection.
"""

from typing import Dict, List, Any, Optional, Union
import os
import logging
import json
from pathlib import Path
import subprocess
import tempfile
import cv2
import numpy as np
from datetime import datetime

from ai_video_pipeline.config.settings import settings
from ai_video_pipeline.tools.asset_librarian import AssetLibrarian

logger = logging.getLogger(__name__)


class MotionQCAgent:
    """
    Motion QC Agent for performing quality checks on video assets.
    
    This agent is responsible for:
    1. Checking video durations against expected ranges
    2. Verifying aspect ratios match project requirements
    3. Detecting duplicate or frozen frames
    4. Identifying other potential quality issues
    """
    
    def __init__(self):
        """Initialize the Motion QC Agent."""
        self.min_duration_seconds = 1.0  # Minimum acceptable clip duration
        self.max_duration_seconds = 60.0  # Maximum acceptable clip duration
        self.target_aspect_ratio = 16/9  # Default target aspect ratio (1080p)
        self.aspect_ratio_tolerance = 0.05  # Tolerance for aspect ratio deviation
        self.duplicate_frame_threshold = 0.98  # Similarity threshold for duplicate frame detection
        self.frozen_frame_sequence_threshold = 15  # Number of consecutive similar frames to flag
        
    def run(
        self,
        asset_manifest: Dict[str, Any],
        output_path: Optional[Path] = None
    ) -> Dict[str, Any]:
        """
        Run the Motion QC Agent to check video assets.
        
        Args:
            asset_manifest: Asset manifest with video references
            output_path: Optional path to save the QC report
            
        Returns:
            Dict[str, Any]: QC report with issues found
        """
        logger.info("Running Motion QC Agent")
        
        # Initialize QC report
        qc_report = {
            "timestamp": datetime.now().isoformat(),
            "job_id": asset_manifest.get("job_id", "unknown"),
            "status": "pass",  # Default to pass, will be changed if issues found
            "issues": [],
            "warnings": [],
            "asset_checks": {}
        }
        
        # Check if there are video assets to analyze
        if "assets" not in asset_manifest or "videos" not in asset_manifest["assets"]:
            qc_report["status"] = "warning"
            qc_report["warnings"].append("No video assets found in manifest")
            return qc_report
        
        # Process each video asset
        for video in asset_manifest["assets"]["videos"]:
            if "path" not in video:
                qc_report["warnings"].append(f"Video asset missing path: {video.get('id', 'unknown')}")
                continue
                
            video_path = video["path"]
            video_id = video.get("id", os.path.basename(video_path))
            
            # Initialize asset check results
            asset_check = {
                "path": video_path,
                "checks": {
                    "duration": {"status": "pass"},
                    "aspect_ratio": {"status": "pass"},
                    "duplicate_frames": {"status": "pass"}
                }
            }
            
            try:
                # Check video duration
                duration_check = self._check_duration(video_path, video.get("metadata", {}))
                asset_check["checks"]["duration"] = duration_check
                
                # Check aspect ratio
                aspect_ratio_check = self._check_aspect_ratio(video_path, video.get("metadata", {}))
                asset_check["checks"]["aspect_ratio"] = aspect_ratio_check
                
                # Check for duplicate frames
                duplicate_frames_check = self._check_duplicate_frames(video_path)
                asset_check["checks"]["duplicate_frames"] = duplicate_frames_check
                
                # Determine overall status for this asset
                asset_status = "pass"
                for check_name, check_result in asset_check["checks"].items():
                    if check_result["status"] == "fail":
                        asset_status = "fail"
                        # Add to global issues list
                        qc_report["issues"].append({
                            "asset_id": video_id,
                            "check": check_name,
                            "message": check_result.get("message", "")
                        })
                    elif check_result["status"] == "warning" and asset_status != "fail":
                        asset_status = "warning"
                        # Add to global warnings list
                        qc_report["warnings"].append({
                            "asset_id": video_id,
                            "check": check_name,
                            "message": check_result.get("message", "")
                        })
                
                asset_check["status"] = asset_status
                
            except Exception as e:
                logger.error(f"Error checking video {video_id}: {str(e)}")
                asset_check["status"] = "error"
                asset_check["error"] = str(e)
                qc_report["issues"].append({
                    "asset_id": video_id,
                    "check": "processing",
                    "message": f"Error processing video: {str(e)}"
                })
            
            # Add asset check results to report
            qc_report["asset_checks"][video_id] = asset_check
        
        # Determine overall QC status
        if len(qc_report["issues"]) > 0:
            qc_report["status"] = "fail"
        elif len(qc_report["warnings"]) > 0:
            qc_report["status"] = "warning"
        
        # Save report if output path is provided
        if output_path:
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            with open(output_path, "w") as f:
                json.dump(qc_report, f, indent=2)
            logger.info(f"QC report saved to {output_path}")
        
        return qc_report
    
    def _check_duration(self, video_path: str, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        Check if video duration is within acceptable range.
        
        Args:
            video_path: Path to the video file
            metadata: Video metadata that might contain duration
            
        Returns:
            Dict[str, Any]: Check result with status and details
        """
        result = {"status": "pass"}
        
        try:
            # Try to get duration from metadata first
            duration = metadata.get("duration_seconds")
            
            # If not available in metadata, extract it using OpenCV
            if duration is None:
                cap = cv2.VideoCapture(video_path)
                if not cap.isOpened():
                    result["status"] = "fail"
                    result["message"] = "Could not open video file"
                    return result
                
                fps = cap.get(cv2.CAP_PROP_FPS)
                frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
                duration = frame_count / fps if fps > 0 else 0
                cap.release()
            
            # Check duration against thresholds
            if duration < self.min_duration_seconds:
                result["status"] = "fail"
                result["message"] = f"Video duration ({duration:.2f}s) is below minimum threshold ({self.min_duration_seconds}s)"
            elif duration > self.max_duration_seconds:
                result["status"] = "warning"
                result["message"] = f"Video duration ({duration:.2f}s) exceeds recommended maximum ({self.max_duration_seconds}s)"
            
            result["duration"] = duration
            
        except Exception as e:
            result["status"] = "error"
            result["message"] = f"Error checking duration: {str(e)}"
        
        return result
    
    def _check_aspect_ratio(self, video_path: str, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        Check if video aspect ratio matches target.
        
        Args:
            video_path: Path to the video file
            metadata: Video metadata that might contain dimensions
            
        Returns:
            Dict[str, Any]: Check result with status and details
        """
        result = {"status": "pass"}
        
        try:
            # Try to get dimensions from metadata first
            width = metadata.get("dimensions", {}).get("width")
            height = metadata.get("dimensions", {}).get("height")
            
            # If not available in metadata, extract it using OpenCV
            if width is None or height is None:
                cap = cv2.VideoCapture(video_path)
                if not cap.isOpened():
                    result["status"] = "fail"
                    result["message"] = "Could not open video file"
                    return result
                
                width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                cap.release()
            
            # Calculate aspect ratio
            aspect_ratio = width / height if height > 0 else 0
            
            # Check aspect ratio against target with tolerance
            ratio_diff = abs(aspect_ratio - self.target_aspect_ratio) / self.target_aspect_ratio
            
            if ratio_diff > self.aspect_ratio_tolerance:
                result["status"] = "warning"
                result["message"] = (
                    f"Video aspect ratio ({aspect_ratio:.3f}) differs from target "
                    f"({self.target_aspect_ratio:.3f}) by {ratio_diff*100:.1f}%"
                )
            
            result["aspect_ratio"] = aspect_ratio
            result["dimensions"] = {"width": width, "height": height}
            
        except Exception as e:
            result["status"] = "error"
            result["message"] = f"Error checking aspect ratio: {str(e)}"
        
        return result
    
    def _check_duplicate_frames(self, video_path: str, sample_rate: int = 5) -> Dict[str, Any]:
        """
        Check for duplicate or frozen frames in video.
        
        Args:
            video_path: Path to the video file
            sample_rate: Only check every Nth frame to improve performance
            
        Returns:
            Dict[str, Any]: Check result with status and details
        """
        result = {"status": "pass"}
        
        try:
            cap = cv2.VideoCapture(video_path)
            if not cap.isOpened():
                result["status"] = "fail"
                result["message"] = "Could not open video file"
                return result
            
            # Initialize variables
            prev_frame = None
            duplicate_sequences = []
            current_sequence = None
            frame_count = 0
            
            while True:
                # Read frame
                ret, frame = cap.read()
                if not ret:
                    break
                
                # Only process every Nth frame
                if frame_count % sample_rate != 0:
                    frame_count += 1
                    continue
                
                # Convert to grayscale for faster comparison
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                gray = cv2.resize(gray, (320, 180))  # Resize for faster processing
                
                if prev_frame is not None:
                    # Calculate similarity between frames
                    similarity = self._calculate_frame_similarity(prev_frame, gray)
                    
                    # Check if frames are similar
                    if similarity > self.duplicate_frame_threshold:
                        # Start or continue a duplicate sequence
                        if current_sequence is None:
                            current_sequence = {
                                "start_frame": frame_count,
                                "frames": 1
                            }
                        else:
                            current_sequence["frames"] += 1
                    else:
                        # End current sequence if it exists
                        if current_sequence is not None:
                            if current_sequence["frames"] >= self.frozen_frame_sequence_threshold:
                                duplicate_sequences.append(current_sequence)
                            current_sequence = None
                
                prev_frame = gray
                frame_count += 1
            
            # Check if the last sequence was a duplicate sequence
            if current_sequence is not None and current_sequence["frames"] >= self.frozen_frame_sequence_threshold:
                duplicate_sequences.append(current_sequence)
            
            cap.release()
            
            # Determine result based on duplicate sequences
            if duplicate_sequences:
                result["status"] = "warning"
                result["message"] = f"Found {len(duplicate_sequences)} sequences of frozen frames"
                result["duplicate_sequences"] = duplicate_sequences
            
        except Exception as e:
            result["status"] = "error"
            result["message"] = f"Error checking duplicate frames: {str(e)}"
        
        return result
    
    def _calculate_frame_similarity(self, frame1: np.ndarray, frame2: np.ndarray) -> float:
        """
        Calculate similarity between two frames.
        
        Args:
            frame1: First frame
            frame2: Second frame
            
        Returns:
            float: Similarity score between 0 and 1
        """
        # Calculate structural similarity index
        try:
            # Calculate mean squared error
            err = np.sum((frame1.astype("float") - frame2.astype("float")) ** 2)
            err /= float(frame1.shape[0] * frame1.shape[1])
            
            # Convert to similarity score (1 - normalized error)
            max_err = 255.0 ** 2  # Maximum possible MSE
            similarity = 1.0 - (err / max_err)
            
            return similarity
        except Exception:
            return 0.0
