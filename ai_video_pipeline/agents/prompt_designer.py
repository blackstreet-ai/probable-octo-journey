"""
Prompt-Designer Agent module.

This module implements the Prompt-Designer Agent, which is responsible for
converting script sections to optimized text prompts for image and video generation.
"""

from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field

# Mock Agent class for testing without OpenAI Agents SDK
class Agent:
    def __init__(self, name, instructions=None, handoffs=None):
        self.name = name
        self.instructions = instructions
        self.handoffs = handoffs or []


class PromptStyle(BaseModel):
    """
    Style parameters for prompt generation.
    
    Args:
        artistic_style: The artistic style for the visuals (e.g., photorealistic, cartoon)
        mood: The mood/emotion to convey (e.g., upbeat, serious)
        lighting: Lighting style (e.g., bright, moody, cinematic)
        camera_angle: Camera perspective (e.g., wide shot, close-up)
        color_palette: Color scheme to use (e.g., vibrant, monochrome)
    """
    artistic_style: str = "photorealistic"
    mood: str = "neutral"
    lighting: str = "natural"
    camera_angle: str = "medium shot"
    color_palette: str = "balanced"
    additional_parameters: Optional[Dict[str, Any]] = None


class GenerationPrompt(BaseModel):
    """
    A structured prompt for image or video generation.
    
    Args:
        section_id: ID of the script section this prompt corresponds to
        positive_prompt: The main prompt text describing what to generate
        negative_prompt: Elements to avoid in the generation
        style: Style parameters for the generation
        reference_images: Optional list of reference image URLs
    """
    section_id: str
    positive_prompt: str
    negative_prompt: str = "blurry, distorted, low quality, text, watermark, logo"
    style: PromptStyle = Field(default_factory=PromptStyle)
    reference_images: Optional[List[str]] = None


class PromptDesignerAgent:
    """
    Prompt-Designer Agent that converts script sections to optimized text prompts
    for image and video generation.
    """
    
    def __init__(self, name: str = "Prompt-Designer"):
        """
        Initialize the Prompt-Designer Agent.
        
        Args:
            name: Name of the agent
        """
        self.name = name
        self.agent = Agent(
            name=name,
            instructions=(
                "You are the Prompt-Designer Agent responsible for converting script "
                "sections into optimized text prompts for image and video generation. "
                "Your job is to analyze the script content and create detailed, "
                "effective prompts that will produce high-quality visuals."
            ),
        )
    
    async def create_prompts(
        self, 
        script_sections: List[Dict[str, Any]],
        style_guide: Optional[Dict[str, Any]] = None
    ) -> List[GenerationPrompt]:
        """
        Create generation prompts from script sections.
        
        Args:
            script_sections: List of script sections to create prompts for
            style_guide: Optional style guide for the prompts
            
        Returns:
            List[GenerationPrompt]: List of generation prompts
        """
        prompts = []
        
        # Default style if none provided
        default_style = PromptStyle()
        if style_guide:
            # Update default style with provided style guide
            for key, value in style_guide.items():
                if hasattr(default_style, key):
                    setattr(default_style, key, value)
        
        for section in script_sections:
            section_id = section.get("section_id", "unknown")
            content = section.get("content", "")
            title = section.get("title", "")
            visuals = section.get("visuals", "")
            
            # Extract the main content without markdown formatting
            # In a real implementation, we would use a more sophisticated
            # approach to extract the key visual elements from the content
            clean_content = content.replace("#", "").strip()
            
            # Combine content, title, and visuals to create a rich prompt
            prompt_text = ""
            if visuals:
                # If visuals are explicitly specified, use them as the primary prompt
                prompt_text = visuals
            else:
                # Otherwise, create a prompt from the title and content
                prompt_text = f"{title}: {clean_content}"
            
            # Create a structured prompt
            prompt = GenerationPrompt(
                section_id=section_id,
                positive_prompt=prompt_text,
                style=default_style.model_copy(),
            )
            
            prompts.append(prompt)
        
        return prompts
    
    def format_for_falai(self, prompt: GenerationPrompt) -> Dict[str, Any]:
        """
        Format a generation prompt for the fal.ai API.
        
        Args:
            prompt: The generation prompt to format
            
        Returns:
            Dict[str, Any]: Formatted prompt for fal.ai
        """
        # Combine the positive prompt with style parameters
        style = prompt.style
        formatted_prompt = (
            f"{prompt.positive_prompt}, "
            f"{style.artistic_style}, {style.mood} mood, "
            f"{style.lighting} lighting, {style.camera_angle}, "
            f"{style.color_palette} colors"
        )
        
        return {
            "prompt": formatted_prompt,
            "negative_prompt": prompt.negative_prompt,
            "section_id": prompt.section_id
        }
