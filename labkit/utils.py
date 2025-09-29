import json
from pathlib import Path

def run(cmd, check=True, silent=False):
    """Run shell command"""
    import subprocess
    try:
        result = subprocess.run(
            cmd, capture_output=silent, text=True, check=check
        )
        return result
    except subprocess.CalledProcessError as e:
        if not silent:
            error(f"❌ Command failed: {' '.join(cmd)}")
            print(e.stderr)
        raise


def ensure_incus_running():
    result = run(["incus", "info"], silent=True, check=False)
    if result.returncode != 0:
        fatal("Incus daemon is not running. Start with: sudo systemctl start incus")
        exit(1)


def get_container_state(name):
    result = run(["incus", "list", name, "--format=json"], silent=True, check=False)
    if result.returncode != 0:
        return None
    try:
        data = json.loads(result.stdout)
        for c in data:
            if c["name"] == name:
                return c["status"]
        return None
    except (json.JSONDecodeError, KeyError) as e:
        warning(f"Failed to parse incus list output: {e}")
        return None
    
def _color(code):
    return f"\033[{code}m"

RED = _color("31")
GREEN = _color("32")
YELLOW = _color("33")
BLUE = _color("34")
BOLD = _color("1")
RESET = _color("0")

def info(msg):
    print(f"{BLUE}ℹ️  {msg}{RESET}")

def success(msg):
    print(f"{GREEN}✅ {msg}{RESET}")

def warning(msg):
    print(f"{YELLOW}⚠️  {msg}{RESET}")

def error(msg):
    print(f"{RED}❌ {msg}{RESET}")

def fatal(msg):
    print(f"{RED}💥 {msg}{RESET}")

def heading(msg):
    print(f"\n{BOLD}{msg}{RESET}")