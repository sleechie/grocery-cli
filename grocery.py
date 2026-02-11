#!/usr/bin/env python3
"""Wrapper script to run the grocery CLI."""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from grocery.cli import main
main()
