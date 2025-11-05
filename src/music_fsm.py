"""Finite State Machine for music generation workflow"""

import time
import logging
from typing import Optional, Callable
from transitions import Machine

from .states import MusicGenerationState, TaskStatus
from .api_client import AIMusicAPIClient, AIMusicAPIError
from .models import MusicGenerationRequest, MusicGenerationResult

logger = logging.getLogger(__name__)


class MusicGenerationFSM:
    """
    Finite State Machine for managing music generation workflow

    States:
    - IDLE: Initial state, ready to start
    - PREPARING: Validating and preparing request
    - CREATING: Sending creation request to API
    - PENDING: Waiting for task to start processing
    - POLLING: Actively checking task status
    - COMPLETED: Task completed successfully
    - DOWNLOADING: Downloading generated music files
    - FAILED: Task failed
    - CANCELLED: Task cancelled by user
    """

    # FSM state transitions
    states = [state.value for state in MusicGenerationState]

    transitions = [
        # From IDLE
        {"trigger": "start", "source": MusicGenerationState.IDLE, "dest": MusicGenerationState.PREPARING},

        # From PREPARING
        {"trigger": "prepared", "source": MusicGenerationState.PREPARING, "dest": MusicGenerationState.CREATING},
        {"trigger": "fail", "source": MusicGenerationState.PREPARING, "dest": MusicGenerationState.FAILED},

        # From CREATING
        {"trigger": "created", "source": MusicGenerationState.CREATING, "dest": MusicGenerationState.PENDING},
        {"trigger": "fail", "source": MusicGenerationState.CREATING, "dest": MusicGenerationState.FAILED},

        # From PENDING
        {"trigger": "poll", "source": MusicGenerationState.PENDING, "dest": MusicGenerationState.POLLING},
        {"trigger": "fail", "source": MusicGenerationState.PENDING, "dest": MusicGenerationState.FAILED},
        {"trigger": "cancel", "source": MusicGenerationState.PENDING, "dest": MusicGenerationState.CANCELLED},

        # From POLLING
        {"trigger": "still_pending", "source": MusicGenerationState.POLLING, "dest": MusicGenerationState.PENDING},
        {"trigger": "complete", "source": MusicGenerationState.POLLING, "dest": MusicGenerationState.COMPLETED},
        {"trigger": "fail", "source": MusicGenerationState.POLLING, "dest": MusicGenerationState.FAILED},
        {"trigger": "cancel", "source": MusicGenerationState.POLLING, "dest": MusicGenerationState.CANCELLED},

        # From COMPLETED
        {"trigger": "download", "source": MusicGenerationState.COMPLETED, "dest": MusicGenerationState.DOWNLOADING},
        {"trigger": "reset", "source": MusicGenerationState.COMPLETED, "dest": MusicGenerationState.IDLE},

        # From DOWNLOADING
        {"trigger": "downloaded", "source": MusicGenerationState.DOWNLOADING, "dest": MusicGenerationState.IDLE},
        {"trigger": "fail", "source": MusicGenerationState.DOWNLOADING, "dest": MusicGenerationState.FAILED},

        # From FAILED
        {"trigger": "reset", "source": MusicGenerationState.FAILED, "dest": MusicGenerationState.IDLE},
        {"trigger": "retry", "source": MusicGenerationState.FAILED, "dest": MusicGenerationState.PREPARING},

        # From CANCELLED
        {"trigger": "reset", "source": MusicGenerationState.CANCELLED, "dest": MusicGenerationState.IDLE},
    ]

    def __init__(
        self,
        api_client: AIMusicAPIClient,
        poll_interval: int = 5,
        max_retries: int = 60,
        on_state_change: Optional[Callable] = None
    ):
        """
        Initialize FSM

        Args:
            api_client: API client instance
            poll_interval: Seconds between status polls
            max_retries: Maximum number of polling attempts
            on_state_change: Callback function called on state transitions
        """
        self.api_client = api_client
        self.poll_interval = poll_interval
        self.max_retries = max_retries
        self.on_state_change_callback = on_state_change

        # State data
        self.request: Optional[MusicGenerationRequest] = None
        self.task_id: Optional[str] = None
        self.result: Optional[MusicGenerationResult] = None
        self.error_message: Optional[str] = None
        self.poll_count: int = 0
        self.start_time: Optional[float] = None

        # Initialize state machine
        self.machine = Machine(
            model=self,
            states=self.states,
            transitions=self.transitions,
            initial=MusicGenerationState.IDLE,
            after_state_change=self._on_state_change,
            ignore_invalid_triggers=True
        )

        logger.info("MusicGenerationFSM initialized")

    def _on_state_change(self):
        """Internal callback for state changes"""
        logger.info(f"State changed to: {self.state}")
        if self.on_state_change_callback:
            self.on_state_change_callback(self.state)

    def generate_music(
        self,
        request: MusicGenerationRequest,
        auto_download: bool = False,
        output_dir: str = "./output"
    ) -> MusicGenerationResult:
        """
        Generate music using FSM workflow

        Args:
            request: Music generation request
            auto_download: Automatically download generated files
            output_dir: Directory to save downloaded files

        Returns:
            MusicGenerationResult with generated clips

        Raises:
            AIMusicAPIError: If generation fails
        """
        self.request = request
        self.start_time = time.time()
        self.poll_count = 0
        self.error_message = None

        try:
            # Start FSM workflow
            logger.info("Starting music generation workflow")
            self.start()

            # Prepare and validate request
            self._prepare_request()

            # Create music generation task
            self._create_task()

            # Poll until completion
            self._poll_until_complete()

            # Check result
            if self.state == MusicGenerationState.COMPLETED:
                # Get final result
                self.result = self.api_client.get_music_result(self.task_id)

                # Calculate generation time
                if self.start_time:
                    self.result.generation_time = time.time() - self.start_time

                # Auto download if requested
                if auto_download and self.result.clips:
                    self._download_files(output_dir)

                logger.info(f"Music generation completed: {len(self.result.clips)} clips generated")
                return self.result

            elif self.state == MusicGenerationState.FAILED:
                raise AIMusicAPIError(self.error_message or "Music generation failed")

            elif self.state == MusicGenerationState.CANCELLED:
                raise AIMusicAPIError("Music generation was cancelled")

            else:
                raise AIMusicAPIError(f"Unexpected final state: {self.state}")

        except Exception as e:
            self.error_message = str(e)
            if self.state != MusicGenerationState.FAILED:
                self.fail()
            logger.error(f"Music generation error: {e}")
            raise

    def _prepare_request(self):
        """Prepare and validate request"""
        logger.info("Preparing request...")

        try:
            # Validate request
            if self.request.custom_mode:
                if not self.request.lyrics or not self.request.style:
                    raise ValueError("Custom mode requires lyrics and style")
            else:
                if not self.request.gpt_description_prompt:
                    raise ValueError("Auto mode requires gpt_description_prompt")

            self.prepared()
            logger.info("Request prepared successfully")

        except Exception as e:
            self.error_message = f"Request preparation failed: {e}"
            self.fail()
            raise

    def _create_task(self):
        """Create music generation task"""
        logger.info("Creating music generation task...")

        try:
            self.task_id = self.api_client.create_music(self.request)
            self.created()
            logger.info(f"Task created: {self.task_id}")

        except Exception as e:
            self.error_message = f"Task creation failed: {e}"
            self.fail()
            raise

    def _poll_until_complete(self):
        """Poll task status until completion"""
        self.poll()

        while self.state == MusicGenerationState.PENDING or self.state == MusicGenerationState.POLLING:
            try:
                # Check if max retries reached
                if self.poll_count >= self.max_retries:
                    self.error_message = "Max polling retries reached"
                    self.fail()
                    break

                self.poll_count += 1
                logger.debug(f"Polling attempt {self.poll_count}/{self.max_retries}")

                # Get task status
                task = self.api_client.get_task_status(self.task_id)

                # Check status
                if task.status == TaskStatus.SUCCESS:
                    logger.info("Task completed successfully")
                    self.complete()
                    break

                elif task.status == TaskStatus.FAILED:
                    self.error_message = task.error_message or "Task failed"
                    logger.error(f"Task failed: {self.error_message}")
                    self.fail()
                    break

                elif task.status in [TaskStatus.PROCESSING, TaskStatus.PENDING, TaskStatus.QUEUED]:
                    logger.debug(f"Task status: {task.status}")
                    self.still_pending()

                    # Wait before next poll
                    time.sleep(self.poll_interval)
                    self.poll()

                else:
                    logger.warning(f"Unknown task status: {task.status}")
                    self.still_pending()
                    time.sleep(self.poll_interval)
                    self.poll()

            except Exception as e:
                self.error_message = f"Polling error: {e}"
                logger.error(self.error_message)
                self.fail()
                break

    def _download_files(self, output_dir: str):
        """Download generated music files"""
        self.download()

        try:
            import os
            os.makedirs(output_dir, exist_ok=True)

            for i, clip in enumerate(self.result.clips):
                if clip.audio_url:
                    filename = f"{self.task_id}_{i}_{clip.id}.mp3"
                    output_path = os.path.join(output_dir, filename)

                    logger.info(f"Downloading clip {i+1}/{len(self.result.clips)}")
                    self.api_client.download_audio(clip.audio_url, output_path)

            self.downloaded()
            logger.info("All files downloaded successfully")

        except Exception as e:
            self.error_message = f"Download failed: {e}"
            logger.error(self.error_message)
            self.fail()
            raise

    def cancel_generation(self):
        """Cancel ongoing music generation"""
        if self.state in [MusicGenerationState.PENDING, MusicGenerationState.POLLING]:
            logger.info("Cancelling music generation")
            self.cancel()

    def reset_fsm(self):
        """Reset FSM to initial state"""
        logger.info("Resetting FSM")
        self.reset()
        self.request = None
        self.task_id = None
        self.result = None
        self.error_message = None
        self.poll_count = 0
        self.start_time = None

    def get_current_state(self) -> str:
        """Get current FSM state"""
        return self.state

    def get_progress(self) -> dict:
        """
        Get current progress information

        Returns:
            Dictionary with progress details
        """
        progress = {
            "state": self.state,
            "task_id": self.task_id,
            "poll_count": self.poll_count,
            "max_retries": self.max_retries,
            "error": self.error_message
        }

        if self.start_time:
            progress["elapsed_time"] = time.time() - self.start_time

        if self.poll_count > 0 and self.max_retries > 0:
            progress["progress_percentage"] = min(100, int((self.poll_count / self.max_retries) * 100))

        return progress
