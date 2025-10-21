# `labkit node remove` – Remove a Node from the Lab

Stops and deletes an Incus container that belongs to the current lab.  
The node’s documentation is preserved in `nodes/<name>/` for audit and reference.

## Syntax

```bash
labkit node remove <name> [flags]
```

### Flags 

table goes here
| flag | default | description |
| --- | --- | --- |
| `<name>` | (required) | Name of the container/node to remove |
| `--force` | `false` | Stop and delete even if the container is running |
| `--dry-run` / `-n` | `false` | Show what would be done without applying changes |
|
 
### Behavior 
`labkit node remove` safely deletes a container while preserving its metadata. 

#### Assumption

- You are inside a valid lab directory (contains `lab.yaml`)
- The node <name> exists as an Incus container
- You want to remove the container but keep its documentation and history
- The container is either stopped or you’ve used `--force`
     
The command: 

1. Validates input:
    - Checks if `<name>` exists in incus list
    - If running and `--force` not used, warns and exits
     
2. Builds an action plan:
    - Stop container (if running and `--force` used)
    - Delete container via incus delete
    - Preserve `nodes/<name>/ directory` and contents
    - Commit removal to Git (message: `labkit: removed node <name>`)
     
3. Executes actions in order
4. Logs event to `logs/YYYYMMDD-HHMMSS-remove-node.txt`
     

**Example**:

```bash
(labkit) ➜  my-project01 git:(master) labkit node rm api-server
[INFO] Planned actions:
  Delete container: api-server
  Preserve documentation in /home/aprksy/workspace/repo/git/project-labs/labs/my-project01/nodes/api-server
  Commit removal to Git
On branch master
nothing to commit, working tree clean
[OK] All actions completed
```

No deletion of node metadata — only the container is removed.
         
## Examples 

Remove a Stopped Node 
```bash
labkit node remove temp-test
```

- Deletes the container
- Keeps `nodes/temp-test/` for future reference
- Commits change to Git
     
Force Remove a Running Node 
```bash
labkit node remove db01 --force
```

- Stops db01 first
- Then deletes it
- Use carefully — no confirmation prompt

Dry Run: Preview Changes 
```bash
labkit node remove api-server --dry-run
```

Output: 
```bash
[INFO] Planned actions:
  Delete container: api-server
  Preserve documentation in /home/aprksy/workspace/repo/git/project-labs/labs/my-project01/nodes/api-server
  Commit removal to Git
[INFO] DRY RUN: No changes applied
```
Safe way to verify intent before deletion.

Combined: Force + Dry Run 
```bash
labkit node remove legacy-app --force --dry-run
``` 

Great for scripting or cleanup automation. 
     
**Tips** 

- Docs are never deleted — `nodes/<name>/` stays for audit trail
- Use `--force` when you know the node is safe to stop
- After removal, you can still view or recover config ideas from `nodes/<name>/`
- The Git history shows who removed the node and when
- To fully clean up (including docs), manually delete `nodes/<name>/` and commit
- Combine with `labkit up`/`down` --only for partial environment control
     
## See Also 

- `labkit` [`node add`](node-add.md)  – Recreate or replace a node
- `labkit` [`down`](down.md)  – Stop nodes without deleting
- [`Configuration Guide`](app_config.md)  – How node lifecycle integrates with lab state
- `labkit` [`requires remove`](requires-rm.md)  – Update dependencies after removal
     