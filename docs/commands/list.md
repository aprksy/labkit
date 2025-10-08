# `labkit list` – List All Discoverable Labs

Displays a table of all labs found across configured search paths.  
Useful for discovering existing projects, auditing environments, or checking lab status.

## Syntax

```bash
labkit list [flags]
```

## Flags 
| flag | default | description |
| --- | --- | --- |
| `--format json` | table | Output as JSON instead of formatted table |
| `--path <dir>` | `$LABKIT_ROOT` or config paths | Override search paths (temporary) |
|
 
## Behavior 

labkit list scans directories to find valid labs — directories containing a lab.yaml file. 

### Assumption 

1. Labs are Git-tracked projects with a standardized structure.
2. Each lab has a `lab.yaml` that defines its name, template, and metadata.
3. Discovery is based on global configuration (`~/.config/labkit/config.yaml`) and environment overrides.
     
The command: 

1. Loads global config (including search_paths)
2. Optionally uses `--path` to override search locations
3. Scans each path (with glob support like `*/projects`)
4. For each directory, checks for `lab.yaml`
5. Reads name, template, and modification time
6. Sorts by last modified (newest first)
7. Outputs in table or JSON format
     
**Example**:
```bash
(labkit) ➜  petshop labkit list

Labs found: 10
NAME               NODES  TEMPLATE       LAST MODIFIED  PATH                      
experiment-12      2      golden-arch    2d ago         /home/aprksy/workspace/sandbox/experiment-12                       
my-other-project   2      golden-arch    2d ago         /home/aprksy/workspace/sandbox/my-other-project                    
telco-project      5      golden-arch    2d ago         /home/aprksy/workspace/labs/telco-project    
my-project01       2      golden-arch    2d ago         /home/aprksy/workspace/labs/my-project01     
jupyter-lab        1      golden-debian  3d ago         /home/aprksy/workspace/labs/jupyter-lab      
learn-programming  2      golden-debian  4d ago         /home/aprksy/workspace/labs/learn-programming
```

No filesystem changes. This is a read-only command. 

Only reads: 
- `~/.config/labkit/config.yaml`
- Each `<lab>/lab.yaml`
     

## Examples 
List All Labs (Default) 

```bash
labkit list
``` 

Scans all paths defined in config and shows interactive table. 
Output as JSON (for scripting) 
```bash
labkit list --format json
[
  {
    "name": "experiment-12",
    "nodes": 2,
    "mtime": 1759586157.6770406,
    "path": "/home/aprksy/workspace/sandbox/experiment-12",
    "template": "golden-arch"
  },
  {
    "name": "my-other-project",
    "nodes": 2,
    "mtime": 1759586032.729813,
    "path": "/home/aprksy/workspace/sandbox/my-other-project",
    "template": "golden-arch"
  },
  {
    "name": "telco-project",
    "nodes": 5,
    "mtime": 1759585545.8005023,
    "path": "/home/aprksy/workspace/labs/telco-project",
    "template": "golden-arch"
  },
  {
    "name": "my-project01",
    "nodes": 2,
    "mtime": 1759584869.9179416,
    "path": "/home/aprksy/workspace/labs/my-project01",
    "template": "golden-arch"
  },
  {
    "name": "jupyter-lab",
    "nodes": 1,
    "mtime": 1759549001.9611955,
    "path": "/home/aprksy/workspace/labs/jupyter-lab",
    "template": "golden-debian"
  },
  {
    "name": "learn-programming",
    "nodes": 2,
    "mtime": 1759411026.9586446,
    "path": "/home/aprksy/workspace/labs/learn-programming",
    "template": "golden-debian"
  }
]

```
 
Useful for automation, CI, or dashboard integration. 
 
Scan Custom Path Temporarily (currently in development)
```bash
labkit list --path /tmp/test-labs --path ~/sandbox
```
 
Ignores config and only scans the specified directories. 

    💡 Does not persist — only for this run. 
     
Combine with grep 
```bash
labkit list | grep postgis
``` 

Filter labs using specific templates. 

**Tips**

Use labkit list after labkit new --allow-scattered to verify discovery
If a lab isn’t showing up, check:
- Does it have `lab.yaml`?
- Is its parent directory in `search_paths`?
- Run `ls ~/.config/labkit/config.yaml` to inspect config
         
In scripts, prefer --format json for reliable parsing
The LAST MODIFIED field reflects when lab.yaml was last changed — good proxy for activity
     

## See Also 

- labkit [`new`](new.md)  – Creates a lab and may auto-add path to config
- labkit [`init`](init.md)  – Initializes a lab in current directory
- [`Configuration Guide`](app_config.md)  – How search_paths works
     