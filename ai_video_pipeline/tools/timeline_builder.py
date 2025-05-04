"""
Timeline Builder for generating FCPXML files.

This module provides functionality for creating Final Cut Pro XML (FCPXML)
files from asset manifests for video editing.
"""

from typing import Dict, Any, List, Optional, Union, Tuple
import os
import json
import xml.etree.ElementTree as ET
import xml.dom.minidom as minidom
from pathlib import Path
import uuid
import logging
from datetime import datetime
import re

from ai_video_pipeline.config.settings import settings

logger = logging.getLogger(__name__)


class TimelineBuilder:
    """
    Timeline Builder for generating FCPXML files.
    
    This class provides methods for creating Final Cut Pro XML (FCPXML)
    files from asset manifests for video editing.
    """
    
    def __init__(self):
        """Initialize the Timeline Builder."""
        self.assets_dir = settings.assets_dir
        self.output_dir = self.assets_dir / "timeline"
        
        # Ensure the output directory exists
        os.makedirs(self.output_dir, exist_ok=True)
    
    def create_fcpxml(
        self,
        asset_manifest: Dict[str, Any],
        output_path: Optional[Path] = None
    ) -> Path:
        """
        Create an FCPXML file from an asset manifest.
        
        Args:
            asset_manifest: Asset manifest with script and media references
            output_path: Optional path to save the FCPXML file
            
        Returns:
            Path: Path to the generated FCPXML file
        """
        logger.info("Creating FCPXML from asset manifest")
        
        # If no output path is provided, create one in the output directory
        if output_path is None:
            project_id = asset_manifest.get("job_id", f"project_{uuid.uuid4().hex[:8]}")
            output_path = self.output_dir / f"{project_id}.fcpxml"
        
        # Create the XML structure
        root = ET.Element("fcpxml", version="1.9")
        resources = ET.SubElement(root, "resources")
        
        # Add a format resource (1080p30)
        format_resource = ET.SubElement(
            resources, 
            "format", 
            id="r1", 
            name="FFVideoFormat1080p30", 
            frameDuration="1/30s", 
            width="1920", 
            height="1080"
        )
        
        # Add library and event elements
        libraries = ET.SubElement(root, "library")
        project_id = asset_manifest.get("job_id", f"project_{uuid.uuid4().hex[:8]}")
        event = ET.SubElement(libraries, "event", name=f"AI Video Project - {project_id}")
        
        # Get project title from script metadata
        project_title = "Untitled Project"
        if "script" in asset_manifest and "title" in asset_manifest["script"]:
            project_title = asset_manifest["script"]["title"]
        
        # Create project element
        project = ET.SubElement(event, "project", name=project_title)
        
        # Calculate total duration based on assets
        total_duration_seconds = self._calculate_total_duration(asset_manifest)
        total_duration = f"{total_duration_seconds}s"
        
        # Create sequence
        sequence = ET.SubElement(project, "sequence", format="r1", duration=total_duration)
        spine = ET.SubElement(sequence, "spine")
        
        # Process and add assets to the timeline
        current_offset = 0.0  # in seconds
        
        # Add asset references to resources
        asset_refs = self._add_asset_references(resources, asset_manifest)
        
        # Add video clips to the timeline
        current_offset = self._add_video_clips(spine, asset_manifest, asset_refs, current_offset)
        
        # Add audio clips to the timeline
        self._add_audio_clips(spine, asset_manifest, asset_refs, 0.0)  # Start audio from the beginning
        
        # Convert the XML to a pretty-printed string
        xml_str = minidom.parseString(ET.tostring(root)).toprettyxml(indent="  ")
        
        # Write the XML to the output file
        with open(output_path, "w") as f:
            f.write(xml_str)
        
        logger.info(f"FCPXML file created at {output_path}")
        return output_path
    
    def _calculate_total_duration(self, asset_manifest: Dict[str, Any]) -> float:
        """
        Calculate the total duration of the timeline based on assets.
        
        Args:
            asset_manifest: Asset manifest with media references
            
        Returns:
            float: Total duration in seconds
        """
        # Start with a minimum duration
        total_duration = 0.0
        
        # Check video assets
        if "assets" in asset_manifest and "videos" in asset_manifest["assets"]:
            for video in asset_manifest["assets"]["videos"]:
                if "metadata" in video and "duration_seconds" in video["metadata"]:
                    total_duration += video["metadata"]["duration_seconds"]
        
        # Check image assets (assume each image is displayed for 5 seconds)
        if "assets" in asset_manifest and "images" in asset_manifest["assets"]:
            total_duration += len(asset_manifest["assets"]["images"]) * 5.0
        
        # Check audio assets (use the longest audio track)
        audio_duration = 0.0
        if "assets" in asset_manifest and "audio" in asset_manifest["assets"]:
            for audio in asset_manifest["assets"]["audio"]:
                if "metadata" in audio and "duration_seconds" in audio["metadata"]:
                    audio_duration = max(audio_duration, audio["metadata"]["duration_seconds"])
        
        # Use the longer of video/image duration or audio duration
        total_duration = max(total_duration, audio_duration)
        
        # Ensure a minimum duration of 10 seconds
        return max(total_duration, 10.0)
    
    def _add_asset_references(self, resources: ET.Element, asset_manifest: Dict[str, Any]) -> Dict[str, str]:
        """
        Add asset references to the resources section and return a mapping of asset paths to resource IDs.
        
        Args:
            resources: Resources XML element
            asset_manifest: Asset manifest with media references
            
        Returns:
            Dict[str, str]: Mapping of asset paths to resource IDs
        """
        asset_refs = {}
        asset_id_counter = 1
        
        # Process video assets
        if "assets" in asset_manifest and "videos" in asset_manifest["assets"]:
            for video in asset_manifest["assets"]["videos"]:
                if "path" in video:
                    asset_id = f"v{asset_id_counter}"
                    asset_id_counter += 1
                    
                    # Create asset element
                    asset_elem = ET.SubElement(
                        resources,
                        "asset",
                        id=asset_id,
                        name=os.path.basename(video["path"]),
                        src=f"file://{video['path']}",
                        start="0s",
                        duration=f"{video.get('metadata', {}).get('duration_seconds', 5.0)}s",
                        hasVideo="1",
                        hasAudio="0",
                        format="r1"
                    )
                    
                    # Add to asset references
                    asset_refs[video["path"]] = asset_id
        
        # Process image assets
        if "assets" in asset_manifest and "images" in asset_manifest["assets"]:
            for image in asset_manifest["assets"]["images"]:
                if "path" in image:
                    asset_id = f"i{asset_id_counter}"
                    asset_id_counter += 1
                    
                    # Create asset element
                    asset_elem = ET.SubElement(
                        resources,
                        "asset",
                        id=asset_id,
                        name=os.path.basename(image["path"]),
                        src=f"file://{image['path']}",
                        start="0s",
                        duration="5s",  # Default duration for images
                        hasVideo="1",
                        hasAudio="0",
                        format="r1"
                    )
                    
                    # Add to asset references
                    asset_refs[image["path"]] = asset_id
        
        # Process audio assets
        if "assets" in asset_manifest and "audio" in asset_manifest["assets"]:
            for audio in asset_manifest["assets"]["audio"]:
                if "path" in audio:
                    asset_id = f"a{asset_id_counter}"
                    asset_id_counter += 1
                    
                    # Create asset element
                    asset_elem = ET.SubElement(
                        resources,
                        "asset",
                        id=asset_id,
                        name=os.path.basename(audio["path"]),
                        src=f"file://{audio['path']}",
                        start="0s",
                        duration=f"{audio.get('metadata', {}).get('duration_seconds', 5.0)}s",
                        hasVideo="0",
                        hasAudio="1",
                        audioSources="1",
                        audioChannels="2",
                        audioRate="48000"
                    )
                    
                    # Add to asset references
                    asset_refs[audio["path"]] = asset_id
        
        return asset_refs
    
    def _add_video_clips(self, spine: ET.Element, asset_manifest: Dict[str, Any], 
                         asset_refs: Dict[str, str], start_offset: float) -> float:
        """
        Add video clips to the timeline spine.
        
        Args:
            spine: Spine XML element
            asset_manifest: Asset manifest with media references
            asset_refs: Mapping of asset paths to resource IDs
            start_offset: Starting offset in seconds
            
        Returns:
            float: New offset after adding clips
        """
        current_offset = start_offset
        
        # Add video clips
        if "assets" in asset_manifest and "videos" in asset_manifest["assets"]:
            for video in asset_manifest["assets"]["videos"]:
                if "path" in video and video["path"] in asset_refs:
                    asset_id = asset_refs[video["path"]]
                    duration = video.get("metadata", {}).get("duration_seconds", 5.0)
                    
                    # Create clip element
                    clip = ET.SubElement(
                        spine,
                        "video",
                        ref=asset_id,
                        offset=f"{current_offset}s",
                        duration=f"{duration}s",
                        name=os.path.basename(video["path"])
                    )
                    
                    # Update offset
                    current_offset += duration
        
        # Add image clips (if no videos or after videos)
        if "assets" in asset_manifest and "images" in asset_manifest["assets"]:
            for image in asset_manifest["assets"]["images"]:
                if "path" in image and image["path"] in asset_refs:
                    asset_id = asset_refs[image["path"]]
                    duration = 5.0  # Default duration for images
                    
                    # Create clip element
                    clip = ET.SubElement(
                        spine,
                        "video",
                        ref=asset_id,
                        offset=f"{current_offset}s",
                        duration=f"{duration}s",
                        name=os.path.basename(image["path"])
                    )
                    
                    # Update offset
                    current_offset += duration
        
        return current_offset
    
    def _add_audio_clips(self, spine: ET.Element, asset_manifest: Dict[str, Any], 
                        asset_refs: Dict[str, str], start_offset: float) -> float:
        """
        Add audio clips to the timeline spine.
        
        Args:
            spine: Spine XML element
            asset_manifest: Asset manifest with media references
            asset_refs: Mapping of asset paths to resource IDs
            start_offset: Starting offset in seconds
            
        Returns:
            float: New offset after adding clips
        """
        current_offset = start_offset
        
        # Add audio clips
        if "assets" in asset_manifest and "audio" in asset_manifest["assets"]:
            for audio in asset_manifest["assets"]["audio"]:
                if "path" in audio and audio["path"] in asset_refs:
                    asset_id = asset_refs[audio["path"]]
                    duration = audio.get("metadata", {}).get("duration_seconds", 5.0)
                    
                    # Create clip element
                    clip = ET.SubElement(
                        spine,
                        "audio",
                        ref=asset_id,
                        offset=f"{current_offset}s",
                        duration=f"{duration}s",
                        name=os.path.basename(audio["path"])
                    )
                    
                    # Update offset
                    current_offset += duration
        
        return current_offset
    
    def generate_mix_request(
        self,
        asset_manifest: Dict[str, Any],
        output_path: Optional[Path] = None
    ) -> Path:
        """
        Generate a mix request JSON file for the Audio-Mixer agent.
        
        Args:
            asset_manifest: Asset manifest with audio references
            output_path: Optional path to save the mix request file
            
        Returns:
            Path: Path to the generated mix request file
        """
        logger.info("Generating mix request from asset manifest")
        
        # If no output path is provided, create one in the output directory
        if output_path is None:
            project_id = asset_manifest.get("job_id", f"project_{uuid.uuid4().hex[:8]}")
            output_path = self.output_dir / f"{project_id}_mix_request.json"
        
        # Find voiceover and music assets
        voiceover_path = ""
        music_path = ""
        
        if "assets" in asset_manifest and "audio" in asset_manifest["assets"]:
            for audio in asset_manifest["assets"]["audio"]:
                # Check metadata to determine if it's a voiceover or music
                metadata = audio.get("metadata", {})
                if "path" in audio:
                    if metadata.get("type") == "voiceover" or "text_content" in metadata:
                        voiceover_path = audio["path"]
                    elif metadata.get("type") == "music" or "music" in audio.get("id", "").lower():
                        music_path = audio["path"]
        
        # If we couldn't determine which is which, use heuristics
        if not voiceover_path and "assets" in asset_manifest and "audio" in asset_manifest["assets"]:
            # Assume the first audio file is voiceover if we can't determine otherwise
            if len(asset_manifest["assets"]["audio"]) > 0:
                voiceover_path = asset_manifest["assets"]["audio"][0].get("path", "")
            
            # If there's a second audio file, assume it's music
            if len(asset_manifest["assets"]["audio"]) > 1 and not music_path:
                music_path = asset_manifest["assets"]["audio"][1].get("path", "")
        
        # Create the mix request
        project_id = asset_manifest.get("job_id", f"project_{uuid.uuid4().hex[:8]}")
        mix_request = {
            "project_id": project_id,
            "created_at": datetime.now().isoformat(),
            "voiceover": {
                "path": voiceover_path,
                "gain": 0.0,  # dB
                "normalize": True
            },
            "music": {
                "path": music_path,
                "gain": -6.0,  # dB
                "duck_amount": -12.0,  # dB
                "duck_threshold": -24.0  # dB
            },
            "output": {
                "path": str(settings.audio_dir / f"{project_id}_mixed.wav"),
                "target_lufs": -14.0,  # LUFS
                "true_peak": -1.0  # dB
            },
            "timeline": {
                "total_duration": self._calculate_total_duration(asset_manifest)
            }
        }
        
        # Write the mix request to the output file
        with open(output_path, "w") as f:
            json.dump(mix_request, f, indent=2)
        
        logger.info(f"Mix request file created at {output_path}")
        return output_path
        
    def validate_fcpxml(self, fcpxml_path: Union[str, Path]) -> Dict[str, Any]:
        """
        Validate an FCPXML file against the schema requirements.
        
        Args:
            fcpxml_path: Path to the FCPXML file to validate
            
        Returns:
            Dict[str, Any]: Validation results with status and any issues found
        """
        logger.info(f"Validating FCPXML file: {fcpxml_path}")
        
        # Convert path to string if it's a Path object
        if isinstance(fcpxml_path, Path):
            fcpxml_path = str(fcpxml_path)
        
        # Check if the file exists
        if not os.path.exists(fcpxml_path):
            return {
                "valid": False,
                "errors": [f"File not found: {fcpxml_path}"],
                "warnings": []
            }
        
        try:
            # Parse the XML file
            tree = ET.parse(fcpxml_path)
            root = tree.getroot()
            
            # Initialize validation results
            validation_result = {
                "valid": True,
                "errors": [],
                "warnings": []
            }
            
            # Check FCPXML version
            if root.tag != "fcpxml":
                validation_result["errors"].append("Root element is not 'fcpxml'")
                validation_result["valid"] = False
            
            version = root.get("version")
            if not version:
                validation_result["errors"].append("Missing 'version' attribute on fcpxml element")
                validation_result["valid"] = False
            elif not re.match(r"^\d+\.\d+$", version):
                validation_result["errors"].append(f"Invalid version format: {version}")
                validation_result["valid"] = False
            
            # Check for resources section
            resources = root.find("resources")
            if resources is None:
                validation_result["errors"].append("Missing 'resources' element")
                validation_result["valid"] = False
            else:
                # Check format resources
                formats = resources.findall("format")
                if not formats:
                    validation_result["errors"].append("No 'format' elements found in resources")
                    validation_result["valid"] = False
                
                # Check asset resources
                assets = resources.findall("asset")
                if not assets:
                    validation_result["warnings"].append("No 'asset' elements found in resources")
            
            # Check for library section
            library = root.find("library")
            if library is None:
                validation_result["errors"].append("Missing 'library' element")
                validation_result["valid"] = False
            else:
                # Check for event section
                events = library.findall("event")
                if not events:
                    validation_result["errors"].append("No 'event' elements found in library")
                    validation_result["valid"] = False
                else:
                    # Check for project section
                    projects = []
                    for event in events:
                        projects.extend(event.findall("project"))
                    
                    if not projects:
                        validation_result["errors"].append("No 'project' elements found in events")
                        validation_result["valid"] = False
                    else:
                        # Check for sequence section
                        sequences = []
                        for project in projects:
                            sequences.extend(project.findall("sequence"))
                        
                        if not sequences:
                            validation_result["errors"].append("No 'sequence' elements found in projects")
                            validation_result["valid"] = False
                        else:
                            # Check for spine section
                            spines = []
                            for sequence in sequences:
                                spines.extend(sequence.findall("spine"))
                            
                            if not spines:
                                validation_result["errors"].append("No 'spine' elements found in sequences")
                                validation_result["valid"] = False
                            else:
                                # Check for clips in spine
                                clips = []
                                for spine in spines:
                                    clips.extend(spine.findall("*"))
                                
                                if not clips:
                                    validation_result["warnings"].append("No clips found in spine")
            
            # Check for asset references
            asset_refs = set()
            for asset in resources.findall("asset"):
                asset_id = asset.get("id")
                if asset_id:
                    asset_refs.add(asset_id)
            
            # Check if all clip references exist in assets
            for spine in root.findall(".//spine"):
                for clip in spine.findall("*"):
                    ref = clip.get("ref")
                    if ref and ref not in asset_refs:
                        validation_result["errors"].append(f"Clip references non-existent asset ID: {ref}")
                        validation_result["valid"] = False
            
            return validation_result
            
        except ET.ParseError as e:
            return {
                "valid": False,
                "errors": [f"XML parsing error: {str(e)}"],
                "warnings": []
            }
        except Exception as e:
            return {
                "valid": False,
                "errors": [f"Validation error: {str(e)}"],
                "warnings": []
            }
