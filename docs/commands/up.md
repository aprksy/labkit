# `labkit up` – Start a Lab and Its Dependencies

Starts all local nodes in the current lab, optionally including required infrastructure nodes.  
Safe, predictable, and supports dry runs for previewing changes.

## Syntax

```bash
labkit up [flags]
```

## Flags
| flag | default | description |
| --- | --- | --- |
| `--only <nodes>` | (all) | Only start specific comma-separated nodes (e.g., web01,db01) |
| `--no-deps` | `false` | Do not start required nodes (declared in requires_nodes) |
| `--dry-run` / `-n` | `false` | Show what would be done without applying changes |
|
 
## Behavior 

labkit up orchestrates startup in a safe, dependency-aware order. 
### Assumption 

1. You are inside a valid lab directory (contains `lab.yaml`)
2. Incus daemon is running
3. Template container (e.g., `golden-base`) exists
4. Required nodes (if any) are already defined via labkit requires add `<node>`
     

The command: 

1. Reads lab.yaml to determine:
    - Local nodes (from `nodes/` directory)
    - Required external nodes (from `requires_nodes`)
   
2. Checks current state of containers via incus list
3. Builds an action plan:
    - First: Start required nodes (if `--no-deps` not set)
    - Then: Start local nodes (filtered by `--only` if used)

4. Shows full plan (in `--dry-run` mode)
5. Executes actions in order
6. Logs event to `logs/YYYYMMDD-HHMMSS-up.txt`
     

**Example**: 
Basic `up`, start all containers within the lab:
```bash
(labkit) ➜  store-lab git:(master) labkit up
[INFO] Planned actions:
  Start local node: database
  Start local node: cache
  Start local node: backend
  Start local node: frontend
  Log up event
[OK] All actions completed
```
No new files created, but logs are appended: 
```bash
logs
└── 2025-10-07T16:50:46-up.txt
```

Log content: 
```text
ACTION: up
USER: aprksy
TIMESTAMP: 2025-10-07T16:50:46
LAB: store-lab
NODES_STARTED: ['database', 'cache', 'backend', 'frontend']
REQUIRES_STARTED: []
FILTERED: None
```
 
## Examples 
Start Entire Lab 
```bash
labkit up
```

- Starts all required nodes (tile-server, etc.)
- Starts all local nodes in nodes/ that aren’t already running
     
Start Only Specific Nodes 
```bash
labkit up --only backend,frontend
``` 

- Only starts backend and frontend (and their required dependencies, if any)
- Skips other local nodes like database, cache
     
Useful for testing or CI. 
 
Start Without Dependencies 
```bash
labkit up --only frontend --no-deps
``` 

- Starts only frontend
- Does not start any required nodes (e.g., Redis, PostGIS)
     
Use when you know dependencies are already running. 
 
Dry Run: Preview Changes 
```bash
labkit up --dry-run
``` 

Output: 
```bash
(labkit) ➜  store-lab git:(master) ✗ labkit up --dry-run
[INFO] Planned actions:
  Start local node: database
  Start local node: cache
  Start local node: backend
  Start local node: frontend
  Log up event
[INFO] DRY RUN: No changes applied
```

💡 Run without --dry-run to apply. 

Safe way to verify intent before execution. 
 
Combined: Selective + Dry Run 
```bash
labkit up --only frontend --no-deps --dry-run
```

Great for scripting and automation pipelines. 
**Tips** 

- Always use `--dry-run` when unsure
- If a required node fails to start, labkit up stops and reports the error
- The order ensures dependencies are ready before local nodes start
- Use `--only` with service names from `nodes/` directory (must match container name)
- Combine with labkit status (future) or incus list to verify result
     
## See Also 

- labkit [`down`](down.md)  – Stop lab nodes
- labkit [`requires add`](requires_add.md)  – Declare dependencies
- labkit [`list`](list.md)  – Find all labs
- [`Configuration Guide`](app_config.md)  – How requires_nodes works
     