"""Deterministic, local voice application launcher.

Matches spoken phrases like 'open notepad' or 'please launch calculator' against
an explicit, user-editable registry of allowed executable paths.
Zero LLM interpretation, zero arbitrary command execution.
"""
import json
import os
import re
import shutil
import subprocess
import sys
from typing import Dict, Optional, Tuple

from log import get_logger

log = get_logger(__name__)

LAUNCH_PREFIXES = (
    r"^(?:please\s+)?open\s+",
    r"^(?:please\s+)?launch\s+",
    r"^(?:please\s+)?start\s+",
)


def load_app_registry(registry_path: Optional[str] = None) -> Dict[str, str]:
    """Load and validate the app launch registry mapping spoken aliases to executable paths."""
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    default_path = os.path.join(project_root, "config", "app_launch_registry.json")

    if not registry_path:
        registry_path = default_path
    elif not os.path.isabs(registry_path):
        candidates = [
            os.path.join(project_root, "config", registry_path),
            os.path.join(project_root, registry_path),
            os.path.abspath(registry_path),
        ]
        for c in candidates:
            if os.path.isfile(c):
                registry_path = c
                break
        else:
            registry_path = os.path.join(project_root, "config", registry_path)

    registry: Dict[str, str] = {}
    if not os.path.isfile(registry_path):
        log.debug("App launch registry not found at %s", registry_path)
        return registry

    try:
        with open(registry_path, "r", encoding="utf-8") as f:
            raw_data = json.load(f)

        if isinstance(raw_data, dict):
            for alias, path in raw_data.items():
                if isinstance(alias, str) and isinstance(path, str):
                    clean_alias = alias.strip().lower()
                    clean_path = path.strip()
                    if clean_alias and clean_path:
                        registry[clean_alias] = clean_path
                        # Validate path existence or command availability on PATH
                        if not os.path.isabs(clean_path) and not shutil.which(clean_path):
                            log.warning("App launch alias %r points to command %r not found on PATH", clean_alias, clean_path)
                        elif os.path.isabs(clean_path) and not os.path.exists(clean_path):
                            log.warning("App launch alias %r points to non-existent path: %s", clean_alias, clean_path)
        log.info("Loaded %d registered voice app launch aliases from %s", len(registry), registry_path)
    except Exception as exc:
        log.error("Failed to load app launch registry from %s: %s", registry_path, exc)

    return registry


def match_app_launch_command(text: str, registry: Dict[str, str]) -> Optional[Tuple[str, str]]:
    """Check if the transcribed utterance is a strict 'open <alias>' voice command.

    Returns:
        (matched_alias, executable_path) if matched, or None.

    Enforces strict full-utterance prefix matching:
    - Utterance must begin with an allowed launch prefix ('open', 'launch', 'start')
    - The remainder must EXACTLY match a registered alias (with optional trailing punctuation).
    - Ordinary sentences starting with 'open' (e.g. 'open the door and let the dog out')
      return None because the remainder is not a registered alias.
    """
    if not text or not registry:
        return None

    cleaned = text.strip().lower()
    # Strip terminal punctuation from utterance
    cleaned = re.sub(r"[.!?]+$", "", cleaned).strip()

    remainder = None
    for prefix_pat in LAUNCH_PREFIXES:
        match = re.match(prefix_pat, cleaned, flags=re.IGNORECASE)
        if match:
            remainder = cleaned[match.end():].strip()
            break

    if not remainder:
        return None

    # Check for exact alias match
    if remainder in registry:
        return (remainder, registry[remainder])

    return None


def launch_registered_app(executable_path: str) -> bool:
    """Launch a locally registered executable detached from the current process."""
    if not executable_path:
        return False

    try:
        # Launch detached without blocking or inheriting standard descriptors
        if sys.platform == "win32":
            # DETACHED_PROCESS = 0x00000008, CREATE_NEW_PROCESS_GROUP = 0x00000200
            flags = 0x00000008 | 0x00000200
            subprocess.Popen(
                executable_path,
                creationflags=flags,
                shell=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        else:
            subprocess.Popen(
                [executable_path],
                start_new_session=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        log.info("Successfully launched application: %s", executable_path)
        return True
    except Exception as exc:
        log.error("Failed to launch application %s: %s", executable_path, exc)
        return False
