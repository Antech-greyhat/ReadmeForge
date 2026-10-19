#!/usr/bin/env python3
"""Compatibility entry point for `python readme_forge.py ...`; prefer the `readme-forge` command."""

import sys

from readme_forge.cli import main

if __name__ == "__main__":
    sys.exit(main())
