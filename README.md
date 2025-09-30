# labkit

> 🧪 Lightweight homelab management for Incus containers (Linux-only)

`labkit` is designed for Linux systems running [Incus](https://github.com/lxc/incus).  
It does not support Windows or macOS.

`labkit` helps you organize container-based development labs with built-in documentation, reproducibility, and team collaboration.

Think of it as **"dev environment scaffolding"** — not enforced, but easy to adopt.

---

## ✅ Features

- `labkit init`: Initialize a new lab (Git repo + structure)
- `labkit node add <name>`: Create a container from template + mount docs
- Self-documenting: Each node gets `manifest.yaml`, `README.md`
- Docs live in container at `/lab/node`
- Shared storage per lab: `./shared/`
- No enforcement — convention over control

Built for developers who want clarity without overhead.

---

## 🚀 Quick Start

```bash
# Install
uv install -e .

# Go to your project dir
mkdir myproject && cd myproject

# Initialize lab
labkit init

# Add a node (calls incus copy golden-base ...)
labkit node add web01

# SSH in (via your incus SSH config)
ssh aprksy@web01

# Shows purpose, notes, maintainer tips
cat /lab/node/README.md
```

## 🧩 Directory Layout 
 
```shell
myproject/
├── lab.yaml           # Lab settings
├── README.md
├── nodes/
│   └── web01/         # Node-specific docs
│       ├── manifest.yaml
│       └── README.md  → mounted → /lab/node
└── shared/            # Persistent outputs
    └── scripts/
 ```
 
## 🔐 Requirements 
- Linux (Ubuntu/Debian/Fedora/etc.)
- Python 3.10+
- [`uv`](https://docs.astral.sh/uv/)
- incus CLI installed and working
- A golden base container (e.g., golden-base)
     
## 📄 License 
MIT 