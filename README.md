# labkit

> Lightweight homelab management for Incus containers (Linux-only)

`labkit` helps you organize container-based development labs with **built-in documentation**, **dependency tracking**, and **safe automation** — all version-controlled via Git.

Think of it as a **developer-first environment orchestrator**: simple to use, easy to adopt, and designed for clarity without enforcement.

---

## Features

- `labkit new <project>`: Create and enter a new lab
- `labkit init`: Initialize current directory as a lab
- `labkit node add/remove`: Manage containers in your lab
- Self-documenting: Each node gets `manifest.yaml`, `README.md`
- Docs live inside container at `/lab/node`
- Shared storage per lab: `./shared/`
- Declare dependencies: `labkit requires add tile-server`
- Bidirectional tracking: Labs → infra, infra ← who uses me?
- Safe cleanup: Stop only non-pinned, unrelated containers
- No enforcement — just smart conventions

Built for developers, homelab admins, and anyone managing multiple Incus environments.

---

## Quick Start

```bash
# Install labkit
uv install -e .

# Create a new lab
labkit new myapp-dev

# Add nodes (clones from golden-base by default)
labkit node add web01
labkit node add db01 --template golden-postgres

# Declare dependency on shared infrastructure
labkit requires add tile-server nexus-cache

# List what this lab needs
labkit requires list
# Output:
# This lab requires:
#   - nexus-cache
#   - tile-server

# Verify required services are running
labkit requires check
# All required nodes are running

# SSH into a node (via your incus SSH config)
ssh aprksy@web01
```
Inside any container:
```shell
# Shows purpose, notes, maintainer tips
cat /lab/node/README.md
```

## Directory Layout
```shell
myapp-dev/
├── lab.yaml                   # Lab config: name, template, dependencies
├── README.md                  # Project overview
├── nodes/
│   ├── web01/                 # Node-specific docs
│   │   ├── manifest.yaml      # Role, tags, owner
│   │   └── README.md          → mounted → /lab/node
│   └── db01/
├── shared/                    # Persistent outputs, scripts
│   └── backups/
└── .git/                      # Version control for intent & history
```
## Infrastructure Dependencies
Use labkit requires to declare that your lab depends on external services:
```shell
labkit requires add tile-server
```

This will: 
1. Adds `tile-server` to requires_nodes: in `lab.yaml`
2. Updates the container:
```shell
incus config set tile-server user.required_by=myapp-dev,...
```

So you can later: 
```shell
# Output: myapp-dev,maps-demo
incus config get tile-server user.required_by
```

Perfect for auditing or preventing accidental shutdowns.
## Available Commands
| Command | Purpose |
|--------|--------|
| `labkit new <name>` | Create + enter + init a new lab |
| `labkit init` | Initialize current dir as a lab |
| `labkit node add <name>` | Create container + mount docs |
| `labkit node remove <name>` | Delete container (keeps docs) |
| `labkit requires add <node>` | Declare dependency on shared node |
| `labkit requires remove <node>` | Remove requirement |
| `labkit requires list` | Show current required nodes |
| `labkit requires check` | Verify all required nodes are running |
| `labkit up` | Start all local nodes and required dependencies |
| `labkit down` | Stop all local nodes (leaves required nodes running by default) |
| `labkit down --suspend-required` | Also stop required nodes if no other lab uses them |
| `labkit down --force-stop-all` | Stop everything, even pinned nodes |
| `labkit list` | Find all labs in `~/workspace/labs` |
| `labkit audit` | Scan containers: stray, pinned, lab-affiliated |
| `labkit * --dry-run` | Preview changes without applying (supported by `up`, `down`, `node add/remove`, `requires add/remove`) |

## Lifecycle Management
Use `labkit up` / `down` to manage your lab’s state:
```shell
# Start the lab and its dependencies
labkit up

# Stop only lab-owned nodes
labkit down

# Also suspend required nodes (if safe)
labkit down --suspend-required

# Force stop everything (use carefully)
labkit down --force-stop-all

labkit up --dry-run
# Output:
# Planned actions:
#    Start required node: tile-server
#    Start local node: web01
# DRY RUN: No changes applied
```

### Selective Startup

Start only specific nodes:

```bash
labkit up --only web01,db01
```
Useful for testing or CI. 

Add `--no-deps` to skip required nodes: 
```bash
labkit up --only worker-1 --no-deps
```
All flags work with `--dry-run`. 

### Selective Shutdown

Stop only specific nodes:

```bash
labkit down --only web01
```
Combine with `--suspend-required` to also stop dependencies:
```bash
labkit down --only worker-1 --suspend-required
```

## Audit & Safety 

labkit tracks bidirectional relationships: 
- Labs declare requires_nodes: [tile-server]
- Shared nodes track user.required_by=lab1,lab2
     

This enables safe automation: 

    Never stop a user.pinned=true node
    Only suspend shared nodes when no active lab depends on them

## Logging 

Every up and down is logged: 
```shell
myproject/logs/
├── 2025-09-25T10:22:18-up.txt
└── 2025-09-25T15:30:05-down.txt
```

Each log includes: 

    Action (up/down)
    User
    Timestamp
    Nodes affected
     
Perfect for auditing or debugging. 
## Encouraging Documentation 

When you add a node: 
- `nodes/<name>/manifest.yaml` and `README.md` are auto-created
- Mounted into container at `/lab/node`
- Commit history preserved even after container removal

Tip: Update the skeleton to reflect reality — it helps everyone (including future-you). 

## Requirements 
- Linux (Ubuntu/Debian/Fedora/etc.)
- Python 3.10+
- uv 
- incus CLI installed and working
- A golden base container (e.g., golden-base)
- Set via `lab.yaml` or --template

## Configuration 
Edit `lab.yaml` to customize: 
```yaml
name: myapp-dev
template: golden-base
requires_nodes:
  - tile-server
  - tile38-server
```
Or override during commands:
```shell
labkit node add api01 --template golden-api
```

## License
MIT