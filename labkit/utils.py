"""
utils.py: module that serve general functionalities for use with lab but not directly
operates in side the lab ops.
"""
import subprocess
import sys

def run(cmd, check=True, silent=False):
    """
    run: runs shell command
    """
    try:
        result = subprocess.run(
            cmd, capture_output=silent, text=True, check=check
        )
        return result
    except subprocess.CalledProcessError as e:
        if not silent:
            error(f"Command failed: {' '.join(cmd)}")
            print(e.stderr)
        raise


def ensure_incus_running():
    """
    ensure_incus_running: ensures incus is running
    """
    result = run(["incus", "info"], silent=True, check=False)
    if result.returncode != 0:
        fatal("Incus daemon is not running. Start with: sudo systemctl start incus")
        sys.exit(1)

def container_exists(name: str) -> bool:
    """
    container_exists: checks if an Incus container or snapshot exists.
    Uses 'incus info' because it's fast and authoritative.
    """
    result = run(
        ["incus", "info", name],
        silent=True,
        check=False
    )
    return result.returncode == 0

def _color(code):
    """
    _color: returns color code that can be use inside terminal
    """
    return f"\033[{code}m"

RED = _color("31")
GREEN = _color("32")
YELLOW = _color("33")
BLUE = _color("34")
BOLD = _color("1")
RESET = _color("0")

def info(msg):
    """
    info: prints message with formatting for INFO
    """
    print(f"{BLUE}[INFO] {msg}{RESET}")

def success(msg):
    """
    success: prints message with formatting for SUCCEEDED event
    """
    print(f"{GREEN}[OK] {msg}{RESET}")

def warning(msg):
    """
    warning: prints message with formatting for WARNING
    """
    print(f"{YELLOW}[WARNING] {msg}{RESET}")

def confirm(msg):
    """
    warning: prints message with formatting for CONFIRM
    """
    print(f"{YELLOW}[WARNING] {msg}{RESET}")

def error(msg):
    """
    error: prints message with formatting for FAILED/ERROR event
    """
    print(f"{RED}[ERROR] {msg}{RESET}")

def fatal(msg):
    """
    fatal: prints message with formatting for unrecoverable failure event
    """
    print(f"{RED}[FATAL] {msg}{RESET}")

def heading(msg):
    """
    heading: prints message with formatting for heading for more results
    """
    print(f"\n{BOLD}{msg}{RESET}")
