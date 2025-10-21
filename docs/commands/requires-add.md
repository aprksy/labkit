# `labkit requires add` – Declare a Required External Node

Declares that the current lab depends on a shared infrastructure node (e.g., `tile-server`, `nexus-cache`).  
Updates both the lab config and the target container’s metadata for bidirectional tracking.

## Syntax

```bash
labkit requires add <node>... [flags]
```

### Flags

| Flag | Default | Description |
|------|--------|------------|
| `<node>...` | (required) | One or more node names to require |
| `--dry-run`, `-n` | `false` | Show what would be done without applying changes |
|

### Behavior

`labkit requires add` establishes a dependency link between your lab and an external service.

#### Assumption

- You are inside a valid lab directory (contains `lab.yaml`)
- The target node (e.g., `tile-server`) exists as an Incus container
- You want to ensure it's running when you run `labkit up`
- You want to track usage via `user.required_by=` label

The command:
1. Validates each `<node>`:
   - Checks if it exists via `incus info <node>`
2. Updates local `lab.yaml`:
   - Adds `<node>` to `requires_nodes:` list
3. Updates remote container metadata:
   - Reads current `user.required_by` value
   - Appends current lab name if not already present
   - Writes back via `incus config set <node> user.required_by=...`
4. Commits changes to Git
5. Logs event to `logs/YYYYMMDD-HHMMSS-requires-add.txt`

This creates a **bidirectional relationship**:
- Lab → "I need `tile-server`"
- `tile-server` → "I am used by `myapp-dev`, `maps-demo`"

**Example**:

```text
[INFO] Planned actions:
  Add 'store-lab' to osm-tile-server.user.required_by
  Save updated lab.yaml
[OK] All actions completed
```

describe the changes in fs, show tree if needed:

Changes in the lab:
```
myproject/
├── lab.yaml                  # Updated: requires_nodes: [tile-server]
├── .git/                     # Auto-committed
└── logs/
    └── 2025-04-05T12:00:00-requires-add.txt
```

On the host (via Incus labels):
```bash
incus config get tile-server user.required_by
# Output: myapp-dev,maps-demo
```

## Examples

### Add a Single Required Node

```bash
labkit requires add tile-server
```

- Adds `tile-server` to `requires_nodes`
- Updates `user.required_by` on `tile-server`

---

### Add Multiple Nodes

```bash
labkit requires add nexus-cache redis-central
```

- Adds both to `lab.yaml`
- Updates each container’s `user.required_by`

---

### Dry Run: Preview Changes

```bash
labkit requires add db-proxy --dry-run
```

Output:
```text
[INFO] Planned actions:
  Add 'store-lab' to osm-tile-server.user.required_by
  Save updated lab.yaml
[INFO] DRY RUN: No changes applied
```

Safe way to verify before modifying system state.

---

### Combined with labkit up

```bash
labkit requires add tile-server
labkit up
```

Now `tile-server` will be started automatically when you run `up`.

## Tips

- Use `requires` for shared, immutable services (tile servers, DNS, package caches)
- Never delete a required node without checking `user.required_by`
- Combine with `user.pinned=true` to prevent accidental shutdown
- If a node doesn’t exist, you’ll get a warning — fix it before `up`
- This command makes `labkit down --suspend-required` safer

## See Also

- [`labkit requires remove`](requires-remove.md) – Remove a requirement
- [`labkit up`](up.md) – Starts required nodes automatically
- [Configuration Guide](../guide/config.md) – How dependency tracking works
