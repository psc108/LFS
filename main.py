#!/usr/bin/env python3
"""
Linux From Scratch Build System
Main entry point for the native GUI application
"""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.gui.main_window import main

if __name__ == "__main__":
    main()