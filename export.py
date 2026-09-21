#!/usr/bin/env python3
"""Compatibility entry point. Prefer python svgdrawer.py --create ID --output FILE."""
import sys
sys.dont_write_bytecode = True
from cli.main import main

if __name__ == '__main__':
    argv = ['--create' if x == '--symbol' else x for x in sys.argv[1:]]
    raise SystemExit(main(argv))
