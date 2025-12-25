# `labkit down` – Stop a Lab’s Nodes

Stops all local nodes in the current lab.  
By default, leaves required infrastructure nodes running — safe for shared environments.

## Syntax

```bash
labkit down [flags]
``` 
 
## Flags 
| flag | default | description |
| --- | --- | --- |
| `--only <nodes>` | (all) | Only stop specific comma-separated nodes (e.g., web01,db01) |
| `--suspend-required` | `false` | Also stop required nodes (if not pinned or used by others) |
| `--force-stop-all` | `false` | Stop everything, even `user.pinned=true` containers |
| `--dry-run` / `-n` | `false` | Show what would be done without applying changes |
|
 
## Behavior 

labkit down safely shuts down lab components while protecting shared infrastructure. 
### Assumption

1. You are inside a valid lab directory (contains `lab.yaml`)
2. The selected backend daemon is running (Incus, Docker, etc.)
3. Required nodes are declared via requires_nodes in `lab.yaml`
4. Shared infrastructure uses backend-specific pinned configuration if it should never be stopped

The command:

1. Reads `lab.yaml` to determine:
    - Local nodes (from `nodes/` directory)
    - Required external nodes (from requires_nodes)
    - Backend to use (from `backend` field)

2. Checks current state of nodes via the selected backend
3. Builds an action plan:
    - First: Stop local nodes (filtered by `--only` if used)
    - Then: Optionally stop required nodes (if `--suspend-required` or `--force-stop-all`)

4. Respects backend-specific pinned configurations unless `--force-stop-all` is used
5. Skips refcount checks for now (future: check `user.required_by=`)
6. Shows full plan (in `--dry-run` mode)
7. Executes actions in order
8. Logs event to `logs/YYYYMMDD-HHMMSS-down.txt`
     

**Example**: 
```bash
(labkit) ➜  store-lab git:(master) ✗ labkit down
[INFO] Planned actions:
  Stop local node: database
  Stop local node: cache
  Stop local node: backend
  Stop local node: frontend
  Log down event
[OK] All actions completed
```
No deletion — only graceful shutdown. 

Logs are appended: 
```bash
logs
├── 2025-10-07T16:50:46-up.txt
├── 2025-10-07T17:24:28-down.txt
├── 2025-10-07T17:24:59-up.txt
├── 2025-10-07T17:25:22-down.txt
├── 2025-10-07T17:31:58-up.txt
├── 2025-10-07T17:32:21-down.txt
├── 2025-10-07T17:33:47-down.txt
├── 2025-10-07T18:04:42-up.txt
└── 2025-10-07T18:04:57-down.txt
```

Log content: 
```bash
ACTION: down
USER: aprksy
TIMESTAMP: 2025-10-07T18:04:57
LAB: store-lab
NODES_STOPPED: ['database', 'cache', 'backend', 'frontend']
REQUIRES_SUSPENDED: []
FILTERED: None
```
## Examples 
Stop All Local Nodes 
```bash
labkit down
``` 

Stops all running local containers in the lab
Leaves required nodes (like `osm-tile-server`) running
Safe for multi-lab environments
     
Stop Only Specific Nodes 
```bash
labkit down --only frontend
```

Only stops `frontend`
Does not touch `database`, `cache`, `backend`.
Useful for rolling restarts or debugging
     
Suspend Required Nodes (If Safe) 

```bash
labkit down --suspend-required
```

Stops local nodes
Also stops required nodes (e.g., `osm-tile-server`)
But skips any container with `user.pinned=true`
     
    ⚠️ Use carefully — don’t break other labs! 
     
Force Stop Everything 
```bash
labkit down --force-stop-all
```

Stops local nodes
Stops required nodes
Even stops containers with `user.pinned=true`
     

🚨 Dangerous — only use when you know no other lab depends on them. 
 
Dry Run: Preview Changes 
```bash
labkit down --dry-run
``` 

Output: 
```bash
[INFO] Planned actions:
  Stop local node: database
  Stop local node: cache
  Stop local node: backend
  Stop local node: frontend
  Log down event
[INFO] DRY RUN: No changes applied
```

Safe way to verify intent before stopping services. 
 
Combined: Selective + Suspend 
```bash
labkit down --only frontend --suspend-required --dry-run
```

Great for CI teardown or maintenance scripts. 
**Tips**

- Use `--suspend-required` when shutting down a dev environment temporarily
- Use `--force-stop-all` only in isolated test labs
- Never assume a required node is “safe” to stop — always check who else uses it
- Combine with labkit up `--only` for partial restarts
- Logs help audit who stopped the lab and when
- Backend-specific pinned configurations may vary (e.g., Incus uses user.pinned, Docker may use labels)

## See Also 

- labkit [`up`](up.md)  – Start lab nodes
- labkit [`requires remove`](requires_rm.md)  – Remove dependency declarations
- labkit [`list`](list.md)  – Find all labs
- [`Configuration Guide`](app_config.md)  – How requires_nodes and labels work
     