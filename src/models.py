"""Data models for Suno API integration"""

from typing import Optional, List, Literal
from pydantic import BaseModel, Field


class MusicGenerationRequest(BaseModel):
    """Request model for music generation"""

    # Mode selection
    custom_mode: bool = Field(
        default=False,
        description="True for custom lyrics/style, False for AI generation"
    )

    # Custom mode fields
    lyrics: Optional[str] = Field(
        default=None,
        description="Custom lyrics (required if custom_mode=True)"
    )
    style: Optional[str] = Field(
        default=None,
        description="Music style/genre (required if custom_mode=True)"
    )
    title: Optional[str] = Field(
        default=None,
        description="Song title"
    )

    # Auto mode fields
    gpt_description_prompt: Optional[str] = Field(
        default=None,
        description="Text description for AI generation (required if custom_mode=False)"
    )

    # Common fields
    make_instrumental: bool = Field(
        default=False,
        description="Generate instrumental version without vocals"
    )
    mv: str = Field(
        default="chirp-v4",
        description="Model version: chirp-v4, chirp-v3.5, etc."
    )
    voice_gender: Optional[Literal["male", "female"]] = Field(
        default=None,
        description="Voice gender for vocals"
    )
    auto_lyrics: bool = Field(
        default=False,
        description="Auto-generate lyrics from description"
    )


class MusicTask(BaseModel):
    """Music generation task information"""

    task_id: str = Field(description="Unique task identifier")
    status: str = Field(description="Current task status")
    clip_ids: Optional[List[str]] = Field(
        default=None,
        description="List of generated clip IDs"
    )
    error_message: Optional[str] = Field(
        default=None,
        description="Error message if task failed"
    )


class MusicClip(BaseModel):
    """Generated music clip information"""

    id: str = Field(description="Clip ID")
    title: Optional[str] = Field(default=None, description="Song title")
    audio_url: Optional[str] = Field(default=None, description="Audio file URL")
    video_url: Optional[str] = Field(default=None, description="Video file URL (if available)")
    image_url: Optional[str] = Field(default=None, description="Cover image URL")
    lyrics: Optional[str] = Field(default=None, description="Song lyrics")
    style: Optional[str] = Field(default=None, description="Music style")
    duration: Optional[float] = Field(default=None, description="Duration in seconds")
    created_at: Optional[str] = Field(default=None, description="Creation timestamp")


class MusicGenerationResult(BaseModel):
    """Complete music generation result"""

    task_id: str = Field(description="Task identifier")
    status: str = Field(description="Final status")
    clips: List[MusicClip] = Field(default_factory=list, description="Generated music clips")
    error: Optional[str] = Field(default=None, description="Error message if failed")
    generation_time: Optional[float] = Field(default=None, description="Total generation time in seconds")
