# Lazyboy Trade Skills
"""
Skills package for Lazyboy trading system.
All skills are imported lazily to avoid circular imports.
"""

import importlib
import sys
from pathlib import Path

# Add skills directory to path
SKILLS_DIR = Path(__file__).parent
if str(SKILLS_DIR) not in sys.path:
    sys.path.insert(0, str(SKILLS_DIR))

# Lazy import helper
def _import_skill(name: str):
    """Import a skill module by name."""
    return importlib.import_module(f".{name}", package="skills")

# Convenience functions - import on demand
def get_macro():
    from . import macro
    return macro

def get_broker_profile():
    from . import broker_profile
    return broker_profile

def get_psychology():
    from . import psychology
    return psychology

def get_sid_tracker():
    from . import sid_tracker
    return sid_tracker

def get_wyckoff():
    from . import wyckoff
    return wyckoff

def get_narrative():
    from . import narrative
    return narrative

def get_journal():
    from . import journal
    return journal

def get_api():
    from . import api
    return api

# Export key functions directly
__all__ = [
    "get_macro",
    "get_broker_profile", 
    "get_psychology",
    "get_sid_tracker",
    "get_wyckoff",
    "get_narrative",
    "get_journal",
    "get_api",
]
