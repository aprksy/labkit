# labkit

> 🧪 Lightweight homelab management for Incus containers (Linux-only)

`labkit` helps you organize container-based development labs with **built-in documentation**, **dependency tracking**, and **safe automation** — all version-controlled via Git.

Think of it as a **developer-first environment orchestrator**: simple to use, easy to adopt, and designed for clarity without enforcement.

---

## ✅ Features

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

## 🚀 Quick Start

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
# 🔌 This lab requires:
#   - nexus-cache
#   - tile-server

# Verify required services are running
labkit requires check
# ✅ All required nodes are running

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
| --- | --- |
| `labkit new <name>` | Create + enter + init a new lab |
| `labkit init` | Initialize current dir as a lab |
| `labkit node add <name>` | Create container + mount docs |
| `labkit node remove <name>` | Delete container (keeps docs) |
| `labkit requires add <node>` | Declare dependency on shared node |
| `labkit requires remove <node>` | Remove requirement |
| `labkit requires list` | Show current required nodes |
| `labkit requires check` | Verify all required nodes are running |
| `labkit list` | Find all labs in `~/workspace/labs` |
| `labkit audit` | Scan containers: `stray`, `pinned`, `lab-affiliated` |

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