#!/usr/bin/env python3
"""
Script to run the audio worker with Celery.

Usage:
    ./run_audio_worker.sh              # Start worker in foreground
    ./run_audio_worker.sh --help       # Show Celery options
    python3 run_audio_worker.py --once # Process 1 job and exit (for CI)
"""

import sys
import os

# Add the src directory to path
sys.path.insert(0, "/Users/hariom/rolplay-ai/agente_rolplay/src")

from agente_rolplay.audio_worker import main

if __name__ == "__main__":
    main()
