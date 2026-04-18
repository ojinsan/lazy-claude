#!/usr/bin/env python3
"""Launcher for telegram-scraper — runs it as a package from the services/ dir."""
import sys
import os
import runpy

# Ensure services/ is on the path so telegram_scraper is importable as a package
services_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, services_dir)

# The folder is named telegram-scraper (dash) — expose it as telegram_scraper via symlink
# or just run main directly after patching the package name
scraper_dir = os.path.join(services_dir, 'telegram-scraper')

# Run main.py as __main__ of the telegram_scraper package
sys.path.insert(0, os.path.dirname(scraper_dir))

# Create a temporary package alias since folder name has a dash
import importlib.util, types

pkg_name = 'telegram_scraper'
if pkg_name not in sys.modules:
    pkg = types.ModuleType(pkg_name)
    pkg.__path__ = [scraper_dir]
    pkg.__package__ = pkg_name
    sys.modules[pkg_name] = pkg

# Re-run main as part of the package
runpy.run_path(os.path.join(scraper_dir, 'main.py'), run_name='__main__',
               init_globals={'__package__': pkg_name, '__spec__': None})
