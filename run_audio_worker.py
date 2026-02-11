#!/usr/bin/env python3
"""
Script de conveniencia para ejecutar el worker de audio con Celery.

Usage:
    ./run_audio_worker.sh              # Inicia worker en foreground
    ./run_audio_worker.sh --help       # Muestra opciones de Celery
    python3 run_audio_worker.py --once # Procesa 1 job y sale (para CI)
"""

import sys
import os

# Agregar el directorio actual al path
sys.path.insert(0, os.path.dirname(__file__))

from audio_worker import main

if __name__ == "__main__":
    main()
