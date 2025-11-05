"""API Client for AIMusicAPI.ai Suno integration"""

import time
import logging
from typing import Optional, Dict, Any
import requests
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from .models import MusicGenerationRequest, MusicTask, MusicClip, MusicGenerationResult
from .states import TaskStatus

logger = logging.getLogger(__name__)


class AIMusicAPIError(Exception):
    """Base exception for API errors"""
    pass


class AIMusicAPIClient:
    """Client for interacting with AIMusicAPI.ai"""

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.aimusicapi.ai/v1",
        timeout: int = 30
    ):
        """
        Initialize API client

        Args:
            api_key: API key for authentication
            base_url: Base URL for API endpoints
            timeout: Request timeout in seconds
        """
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        })

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(requests.exceptions.RequestException)
    )
    def _request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Make HTTP request to API

        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint path
            data: Request body data
            params: URL query parameters

        Returns:
            Response JSON data

        Raises:
            AIMusicAPIError: If request fails
        """
        url = f"{self.base_url}/{endpoint.lstrip('/')}"

        try:
            logger.debug(f"Making {method} request to {url}")
            response = self.session.request(
                method=method,
                url=url,
                json=data,
                params=params,
                timeout=self.timeout
            )

            response.raise_for_status()
            result = response.json()

            logger.debug(f"Response: {result}")
            return result

        except requests.exceptions.HTTPError as e:
            error_msg = f"HTTP error: {e}"
            if e.response is not None:
                try:
                    error_data = e.response.json()
                    error_msg = f"API error: {error_data.get('message', str(e))}"
                except:
                    pass
            logger.error(error_msg)
            raise AIMusicAPIError(error_msg) from e

        except requests.exceptions.RequestException as e:
            logger.error(f"Request error: {e}")
            raise AIMusicAPIError(f"Request failed: {e}") from e

    def create_music(self, request: MusicGenerationRequest) -> str:
        """
        Create a music generation task

        Args:
            request: Music generation request parameters

        Returns:
            Task ID for tracking generation progress

        Raises:
            AIMusicAPIError: If task creation fails
        """
        # Prepare request data
        data = {
            "custom_mode": request.custom_mode,
            "make_instrumental": request.make_instrumental,
            "mv": request.mv,
        }

        if request.custom_mode:
            if not request.lyrics or not request.style:
                raise ValueError("lyrics and style are required in custom mode")
            data["lyrics"] = request.lyrics
            data["style"] = request.style
            if request.title:
                data["title"] = request.title
        else:
            if not request.gpt_description_prompt:
                raise ValueError("gpt_description_prompt is required in auto mode")
            data["gpt_description_prompt"] = request.gpt_description_prompt

        if request.voice_gender:
            data["voice_gender"] = request.voice_gender

        if request.auto_lyrics:
            data["auto_lyrics"] = request.auto_lyrics

        logger.info(f"Creating music generation task with mode: {'custom' if request.custom_mode else 'auto'}")

        # Make API request
        response = self._request("POST", "/suno/create-music", data=data)

        # Extract task ID
        task_id = response.get("data", {}).get("task_id")
        if not task_id:
            raise AIMusicAPIError("No task_id in response")

        logger.info(f"Task created successfully: {task_id}")
        return task_id

    def get_task_status(self, task_id: str) -> MusicTask:
        """
        Get status of a music generation task

        Args:
            task_id: Task identifier

        Returns:
            MusicTask object with current status

        Raises:
            AIMusicAPIError: If status check fails
        """
        logger.debug(f"Checking status for task: {task_id}")

        response = self._request("GET", f"/suno/get-music/{task_id}")

        data = response.get("data", {})

        # Parse response
        status = data.get("status", "unknown")
        clip_ids = []
        clips_data = data.get("clips", [])

        if isinstance(clips_data, list) and clips_data:
            clip_ids = [clip.get("id") for clip in clips_data if clip.get("id")]

        error_message = data.get("error_message") or data.get("message")

        return MusicTask(
            task_id=task_id,
            status=status,
            clip_ids=clip_ids,
            error_message=error_message
        )

    def get_music_result(self, task_id: str) -> MusicGenerationResult:
        """
        Get complete music generation result

        Args:
            task_id: Task identifier

        Returns:
            MusicGenerationResult with all generated clips

        Raises:
            AIMusicAPIError: If result retrieval fails
        """
        logger.info(f"Fetching music result for task: {task_id}")

        response = self._request("GET", f"/suno/get-music/{task_id}")

        data = response.get("data", {})
        status = data.get("status", "unknown")

        clips = []
        clips_data = data.get("clips", [])

        if isinstance(clips_data, list):
            for clip_data in clips_data:
                clip = MusicClip(
                    id=clip_data.get("id", ""),
                    title=clip_data.get("title"),
                    audio_url=clip_data.get("audio_url"),
                    video_url=clip_data.get("video_url"),
                    image_url=clip_data.get("image_url"),
                    lyrics=clip_data.get("lyrics"),
                    style=clip_data.get("style"),
                    duration=clip_data.get("duration"),
                    created_at=clip_data.get("created_at")
                )
                clips.append(clip)

        error = data.get("error_message") or data.get("message") if status == "failed" else None

        return MusicGenerationResult(
            task_id=task_id,
            status=status,
            clips=clips,
            error=error
        )

    def check_credits(self) -> Dict[str, Any]:
        """
        Check available API credits

        Returns:
            Dictionary with credit information

        Raises:
            AIMusicAPIError: If credit check fails
        """
        logger.info("Checking API credits")
        response = self._request("GET", "/credits")
        return response.get("data", {})

    def download_audio(self, url: str, output_path: str) -> None:
        """
        Download audio file from URL

        Args:
            url: Audio file URL
            output_path: Local path to save file

        Raises:
            AIMusicAPIError: If download fails
        """
        try:
            logger.info(f"Downloading audio from {url}")
            response = requests.get(url, timeout=self.timeout, stream=True)
            response.raise_for_status()

            with open(output_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)

            logger.info(f"Audio saved to {output_path}")

        except Exception as e:
            logger.error(f"Download failed: {e}")
            raise AIMusicAPIError(f"Failed to download audio: {e}") from e

    def close(self):
        """Close the HTTP session"""
        self.session.close()
