# `labkit requires remove` – Remove a Required External Node

Removes a dependency declaration from the current lab.  
Also updates the target container’s `user.required_by` label if this lab was listed.

## Syntax

```bash
labkit requires remove <node>... [flags]
```

### Flags

| Flag | Default | Description |
|------|--------|------------|
| `<node>...` | (required) | One or more node names to unrequire |
| `--dry-run`/ `-n` | `false` | Show what would be done without applying changes |
|

### Behavior

`labkit requires remove` safely breaks a dependency link between your lab and an external service.

#### Assumption

- You are inside a valid lab directory (contains `lab.yaml`)
- The node is currently listed in `requires_nodes`
- You no longer need it to start with your lab
- You want to clean up bidirectional tracking

The command:
1. Validates each `<node>`:
   - Checks if it’s in current `requires_nodes`
2. Removes from `lab.yaml`
3. Updates remote container:
   - Reads `user.required_by` list
   - Removes current lab name
   - If list becomes empty, unsets the label
   - Otherwise saves updated comma-separated list
4. Commits change to Git
5. Logs event to `logs/YYYYMMDD-HHMMSS-requires-remove.txt`

This maintains **accurate dependency tracking** across your environment.

**Example**:

```text
[INFO] Planned actions:
  Remove 'store-lab' from osm-tile-server.user.required_by
  Save updated lab.yaml
[OK] All actions completed
```

describe the changes in fs, show tree if needed:

Changes in the lab:
```
myproject/
├── lab.yaml                  # Updated: removes tile-server from requires_nodes
├── .git/                     # Auto-committed
└── logs/
    └── 2025-04-05T12:05:18-requires-remove.txt
```

On the host:
```bash
incus config get tile-server user.required_by
# Output: maps-demo  # (if myapp-dev was removed)
```

## Examples

### Remove a Single Requirement

```bash
labkit requires remove tile-server
```

- Removes from `lab.yaml`
- Updates `user.required_by` on `tile-server`

---

### Remove Multiple Nodes

```bash
labkit requires remove nexus-cache redis-central
```

- Cleans up multiple dependencies at once

---

### Dry Run: Preview Changes

```bash
labkit requires remove db-proxy --dry-run
```

Output:
```text
[INFO] Planned actions:
  Remove 'store-lab' from osm-tile-server.user.required_by
  Save updated lab.yaml
[INFO] DRY RUN: No changes applied
```

Useful before tearing down a lab.

---

### After Removing, Stop Manually

```bash
labkit requires remove tile-server
labkit down
# tile-server remains running unless --suspend-required
```

Perfect for graceful decommissioning.

## Tips

- Removing a requirement does **not** stop the node — use `--suspend-required` with `down` for that
- Always check if other labs still depend on the node before removing
- Use `incus config get <node> user.required_by` to audit
- If you remove by mistake, just `labkit requires add` again
- Git history preserves intent — even after removal

## See Also

- `labkit` [`requires add`](requires-add.md) – Re-establish a dependency
- `labkit` [`down`](down.md) – Use with `--suspend-required` to stop required nodes
- [Configuration Guide](app_config.md) – How bidirectional tracking works
