"""Basic music generation example"""

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
    """Generate music using AI description"""

    # Load configuration
    config = load_config()

    # Setup logging
    setup_logging(log_level=config.log_level, log_file=config.log_file)

    print("=== Suno Music Generation - Basic Example ===\n")

    # Create API client
    client = AIMusicAPIClient(
        api_key=config.api_key,
        base_url=config.base_url,
        timeout=config.timeout
    )

    # Check credits
    try:
        credits = client.check_credits()
        print(f"Available credits: {credits}\n")
    except Exception as e:
        print(f"Warning: Could not check credits: {e}\n")

    # Create FSM
    def on_state_change(state):
        """Callback for state changes"""
        print(f"[FSM] State: {state}")

    fsm = MusicGenerationFSM(
        api_client=client,
        poll_interval=config.poll_interval,
        max_retries=config.max_retries,
        on_state_change=on_state_change
    )

    # Create music generation request (Auto mode)
    request = MusicGenerationRequest(
        custom_mode=False,
        gpt_description_prompt="A cheerful acoustic guitar melody with uplifting vocals, perfect for a summer day",
        make_instrumental=False,
        mv="chirp-v4",
        voice_gender="female"
    )

    print(f"Request: {request.gpt_description_prompt}")
    print(f"Mode: Auto generation")
    print(f"Model: {request.mv}\n")

    # Generate music
    try:
        print("Starting music generation...\n")

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
            if clip.lyrics:
                print(f"  Lyrics: {clip.lyrics[:100]}...")
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
