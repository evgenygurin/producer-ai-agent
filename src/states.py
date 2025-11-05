"""FSM States for music generation workflow"""

from enum import Enum


class MusicGenerationState(str, Enum):
    """States for the music generation FSM"""

    # Initial state
    IDLE = "idle"

    # Request preparation
    PREPARING = "preparing"

    # Creating music task
    CREATING = "creating"

    # Waiting for task completion
    PENDING = "pending"

    # Polling task status
    POLLING = "polling"

    # Task completed successfully
    COMPLETED = "completed"

    # Download music file
    DOWNLOADING = "downloading"

    # Error state
    FAILED = "failed"

    # Cancelled by user
    CANCELLED = "cancelled"


class TaskStatus(str, Enum):
    """Task status from API"""

    PROCESSING = "processing"
    PENDING = "pending"
    SUCCESS = "success"
    FAILED = "failed"
    QUEUED = "queued"
