# `labkit node add` – Add a Node to the Lab

Creates a new Incus container from a template and integrates it into the lab with auto-generated documentation.  
Each node gets its own `manifest.yaml` and `README.md`, mounted inside the container for on-node reference.

## Syntax

```bash
labkit node add <name> [flags]
```

### Flags 

table goes here
| flag | default | description |
| --- | --- | --- |
| `<name>` | (required) | Name of the new container/node |
| `--template <name>` | `default_template` from config | Use specific base container instead of default |
| `--dry-run` / `-n` | `false` | Show what would be done without applying changes |
| 

### Behavior 

`labkit node add` creates a fully documented, integrated node in one command.

#### Assumption

- You are inside a valid lab directory (contains `lab.yaml`)
- The template container (e.g., `golden-base`) exists and is accessible
- Incus daemon is running
- User has write access to the current directory and Incus
     
The command: 

1. Validates input:
    - Ensures container name is valid (alphanumeric, hyphen)
    - Checks that <name> doesn’t already exist as a container
         
2. Resolves template:
    - Uses --template if provided
    - Otherwise uses default_template from global config
         
3. Creates actions plan (in dry-run mode):
    - Clone container from template
    - Create `nodes/<name>/ directory`
    - Generate `manifest.yaml` and `README.md`
    - Mount `nodes/<name>` → `/lab/node` in container
    - Mount `shared/` → `/lab/shared` (if enabled)
    - Apply labels: `user.lab=<lab-name>`, `user.managed-by=labkit`
    - Commit metadata to Git
         
4. Executes all steps atomically
5. Logs event to `logs/YYYYMMDD-HHMMSS-add-node.txt`
     
**Example**:

```bash
(labkit) ➜  my-project01 git:(master) ✗ labkit node add api-server 
[INFO] Planned actions:
  Create container 'api-server' from 'golden-arch'
  Unset inherited template marker on 'api-server'
  Create directory /home/aprksy/workspace/repo/git/project-labs/labs/my-project01/nodes/api-server
  Generate /home/aprksy/workspace/repo/git/project-labs/labs/my-project01/nodes/api-server/manifest.yaml
  Generate /home/aprksy/workspace/repo/git/project-labs/labs/my-project01/nodes/api-server/README.md
  Mount /home/aprksy/workspace/repo/git/project-labs/labs/my-project01/nodes/api-server → api-server:/lab/node
  Mount /home/aprksy/workspace/repo/git/project-labs/labs/my-project01/shared → api-server:/lab/shared
  Set labels on api-server
  Commit node metadata to Git
Device lab-node added to api-server
Device lab-shared added to api-server
[master fb1aab5] labkit: added node api-server
 4 files changed, 22 insertions(+), 11 deletions(-)
 create mode 100644 README.md
 create mode 100644 nodes/api-server/README.md
 create mode 100644 nodes/api-server/manifest.yaml
```

File system changes:
```bash
.
├── lab.yaml
├── nodes
│   └── api-server
│       ├── manifest.yaml
│       └── README.md
├── README.md
└── shared
```

Inside container:
```bash
/lab/node/manifest.yaml
/lab/node/README.md
/lab/shared/    # (if shared storage enabled)
```
         
## Examples 

Add a Node with Default Template 
```bash
labkit node add api-server
```

- Clones from default_template (e.g., golden-base)
- Scaffolds docs
- Mounts directories
- Commits to Git

Use Custom Template 
```bash
labkit node add db-postgis --template golden-postgis
```

- Uses golden-postgis as base image
- Ideal for specialized services
     
Dry Run: Preview Changes 
```bash
labkit node add worker-1 --dry-run
```
Safe way to verify before creation.

Combined: Template + Dry Run 
```bash
labkit node add cache-node --template golden-redis --dry-run
```

Great for scripting or CI pipeline validation. 

**Tips** 

- Node names become container names — use lowercase, numbers, hyphens only
- Edit `nodes/<name>/README.md` to document purpose, ports, configs, gotchas
- Docs are mounted read-write — users can update them from inside the container
- Always commit doc changes back to Git
- Use labkit node remove `<name>` to delete the container (keeps docs)

## See Also 
- `labkit` [`node remove`](node-rm.md)  – Delete a node
- `labkit` [`requires add`](requires-add.md)  – Declare shared dependencies
- [`Configuration Guide`](app_config.md)  – How default_template works
- [`labkit up`](up.md)  – Start nodes after creation
     