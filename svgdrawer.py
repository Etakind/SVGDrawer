#!/usr/bin/env python3
"""SVGDrawer terminal entry point. Run --help, or read docs/AGENT_GUIDE.md."""
import sys
sys.dont_write_bytecode = True
from cli.main import main

if __name__ == '__main__':
    raise SystemExit(main())
