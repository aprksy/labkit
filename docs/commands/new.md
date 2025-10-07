# `labkit new <name>` – Create a New Lab

Creates a new lab directory, initializes it, and enters the directory.

This is the recommended way to start a new project with `labkit`.

## Syntax

```bash
labkit new <name> [flags]
```
 
Positional Argument 
| arg | description |
| --- | --- |
| `<name>` | Name of the new lab. A directory with this name will be created. |
|
 
### Flags 
| flag | default | description |
| --- | --- | --- |
| `--template <name>` | `golden-base` | Use a specific container template instead of the default |
| `--force` / `-f` | `false` | Overwrite existing directory if present |
| `--allow-scattered` | `false` | Allow creation outside default root; auto-add parent path to global config |
|

### Behavior 

#### Assumption

    The command is executed in the default labs root directory defined in [app config](app_config.md). This assumption is made with expectation for labs directories are organized under a single, predefined, centralized and easy to find root directory.

1. Creates a new directory: ./<name> (relative to default labs root)
2. Changes into that directory
3. Runs labkit init inside it
4. Initializes Git repo (if not already under version control)
5. Generates initial files:
```
  lab.yaml    – Lab configuration
  README.md   – Project overview
  nodes/      – Directory for node definitions
  shared/     – Shared assets folder
```

**Example**:

With the default labs root dir `/home/aprksy/workspace/repo/git/project-labs/labs`, output of successful operation should be:
```bash
(labkit) ➜  labs ➜ labkit new labx01   
[INFO] Created and entered directory: /home/aprksy/workspace/repo/git/project-labs/labs/labx01
hint: Using 'master' as the name for the initial branch. This default branch name
hint: is subject to change. To configure the initial branch name to use in all
hint: of your new repositories, which will suppress this warning, call:
hint:
hint: 	git config --global init.defaultBranch <name>
hint:
hint: Names commonly chosen instead of 'master' are 'main', 'trunk' and
hint: 'development'. The just-created branch can be renamed via this command:
hint:
hint: 	git branch -m <name>
hint:
hint: Disable this message with "git config set advice.defaultBranchName false"
Initialized empty Git repository in /home/aprksy/workspace/repo/git/project-labs/labs/labx01/.git/
[master (root-commit) 533fd5c] labkit: initial commit
 1 file changed, 12 insertions(+)
 create mode 100644 lab.yaml
[OK] Lab initialized at /home/aprksy/workspace/repo/git/project-labs/labs/labx01
[INFO] Next: labkit node add <name>
[OK] Initialized empty lab 'labx01'
```

The new labs directory should be:
```bash
(labkit) ➜  labs ➜ tree labx01 
labx01
├── lab.yaml
├── nodes
├── README.md
└── shared

3 directories, 2 files
```
**What if `new` executed outside default labs root directory?**

By default, using the same command should output:
```bash
(labkit) ➜  my-online-store ➜ labkit new store-lab
[ERROR] Cannot create lab outside the default root.
[INFO] If this is intentional, use flag --allow-scattered.
```
The error is to prevent you from making inconsistent location with the lab directory. However, if you intentionally to create the lab outside the default labs root directory you can use the `--allow-scattered` flag in the command.    Possible use case, you're running a side project and want everything related to the project are resided in one place.

When `--allow-scattered` is used, labkit will do the following before the default action above performed:

1. Adds the parent directory (e.g., `/tmp/experimental`) to `~/.config/labkit/config.yaml`
2. Ensures labkit list will discover this lab in the future

Executing the command in a directory out side the default labs root, in this case `/home/aprksy/workspace/sandbox/my-online-store/` should be:
```bash
(labkit) ➜  my-online-store ➜ labkit new store-lab --allow-scattered
Added '/home/aprksy/workspace/sandbox/my-online-store' to lab search paths
[INFO] Created and entered directory: /home/aprksy/workspace/sandbox/my-online-store/store-lab

# same with above ...

[OK] Lab initialized at /home/aprksy/workspace/sandbox/my-online-store/store-lab
[INFO] Next: labkit node add <name>
[OK] Initialized empty lab 'store-lab'
```
         
## Examples 
Basic Usage 
```bash
# Creates and enters myapp-dev/, initializes structure. 
labkit new myapp-dev
```
 
With Custom Template 
```bash
# Uses golden-api as base container template. 
labkit new api-service --template golden-api
```

Force Recreate 
```bash
# Deletes and recreates the directory if it exists. 
labkit new legacy-project --force
``` 
 
Scattered Mode (Opt-In Discovery) 
```bash
# Creates /tmp/sandbox/test-lab
# Adds /tmp/sandbox to global search paths
# Now labkit list will include labs in /tmp/sandbox/*
cd /tmp/sandbox
labkit new test-lab --allow-scattered
```
Use sparingly. Encourages organization over sprawl. 
     
**Tips** 

    The lab name becomes the directory name and is used in lab.yaml
    You can edit lab.yaml after creation to change settings
    All generated files are Git-tracked automatically
     

See Also 

- labkit [`init`](init.md)  – Initialize current directory as a lab
- labkit [`list`](list.md)  – Find all discoverable labs
     