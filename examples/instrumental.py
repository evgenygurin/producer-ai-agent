"""Instrumental music generation example"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.config import load_config
from src.logger import setup_logging
from src.api_client import AIMusicAPIClient
from src.music_fsm import MusicGenerationFSM
from src.models import MusicGenerationRequest


def main():
    """Generate instrumental music"""

    # Load configuration
    config = load_config()

    # Setup logging
    setup_logging(log_level=config.log_level, log_file=config.log_file)

    print("=== Suno Music Generation - Instrumental ===\n")

    # Create API client
    client = AIMusicAPIClient(
        api_key=config.api_key,
        base_url=config.base_url,
        timeout=config.timeout
    )

    # Create FSM
    def on_state_change(state):
        """Callback for state changes"""
        progress = fsm.get_progress()
        if "progress_percentage" in progress:
            print(f"[FSM] State: {state} - Progress: {progress['progress_percentage']}%")
        else:
            print(f"[FSM] State: {state}")

    fsm = MusicGenerationFSM(
        api_client=client,
        poll_interval=config.poll_interval,
        max_retries=config.max_retries,
        on_state_change=on_state_change
    )

    # Create instrumental music request
    request = MusicGenerationRequest(
        custom_mode=False,
        gpt_description_prompt="Epic cinematic orchestral piece with powerful strings and dramatic percussion, perfect for movie trailers",
        make_instrumental=True,  # No vocals
        mv="chirp-v4"
    )

    print(f"Request: {request.gpt_description_prompt}")
    print(f"Mode: Instrumental")
    print(f"Model: {request.mv}\n")

    # Generate music
    try:
        print("Starting instrumental music generation...\n")

        result = fsm.generate_music(
            request=request,
            auto_download=config.auto_download,
            output_dir=config.output_dir
        )

        print(f"\n=== Generation Complete ===")
        print(f"Task ID: {result.task_id}")
        print(f"Status: {result.status}")
        print(f"Generation time: {result.generation_time:.2f} seconds")
        print(f"Clips generated: {len(result.clips)}\n")

        # Display clips info
        for i, clip in enumerate(result.clips, 1):
            print(f"Clip {i}:")
            print(f"  ID: {clip.id}")
            print(f"  Title: {clip.title}")
            print(f"  Duration: {clip.duration}s")
            print(f"  Audio URL: {clip.audio_url}")
            print(f"  Style: {clip.style}")
            print()

        print(f"Files saved to: {config.output_dir}/")

    except Exception as e:
        print(f"\nError: {e}")
        print(f"FSM State: {fsm.get_current_state()}")
        sys.exit(1)

    finally:
        client.close()


if __name__ == "__main__":
    main()
