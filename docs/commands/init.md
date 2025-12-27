# `labkit init` – Initialize a New Lab

Initialize a new lab in the current directory.

## Syntax

```bash
labkit init [flags]
```
 
### Flags
| flag | default | description |
| --- | --- | --- |
| `--name <name>` | Directory name | Set custom lab name (used in lab.yaml) |
| `--template <name>` | `golden-base` | Use a specific template instead of the default |
| `--backend <backend>` | `incus` | Backend to use (incus, docker, qemu) |
| `--allow-scattered` | `false` | Allow creation outside default root; auto-add parent path to global config |
|

### Behavior 

#### Assumption

    The command is executed in a directory under the default labs root directory defined in [app config](app_config.md). This assumption is made with expectation for labs directories are organized under a single, predefined, centralized and easy to find root directory.

1. Checks if `lab.yaml` already exists → skips if yes
2. Creates essential directories:
    - `nodes/` – For node metadata and docs
    - `shared/` – For shared assets across nodes
     
3. Generates files:
    - `lab.yaml` – Configuration file with name, template, user
    - `README.md` – Placeholder project description
     
4. Initializes Git repo if not already in one
5. Commits initial state

**Example**:

With the current dir `/home/aprksy/workspace/repo/git/project-labs/labs/tiny-services`, output of successful operation should be:
```bash
(labkit) ➜  tiny-services ➜ labkit init                           
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
Initialized empty Git repository in /home/aprksy/workspace/repo/git/project-labs/labs/tiny-services/.git/
[master (root-commit) 2772db6] labkit: initial commit
 1 file changed, 12 insertions(+)
 create mode 100644 lab.yaml
[OK] Lab initialized at /home/aprksy/workspace/repo/git/project-labs/labs/tiny-services
[INFO] Next: labkit node add <name>
[OK] Initialized empty lab 'tiny-services'
```

The tiny-services directory should be:
```bash
(labkit) ➜  labs ➜ tree tiny-services
tiny-services
├── lab.yaml
├── nodes
├── README.md
└── shared

3 directories, 2 files
```
**What if `init` executed in directory outside default labs root directory?**

By default, using the same command should output:
```bash
(labkit) ➜  petshop ➜ labkit init
[ERROR] Cannot create lab outside the default root.
[INFO] If this is intentional, use flag --allow-scattered.
```
The error is to prevent you from making inconsistent location with the lab directory. However, if you intentionally to create the lab outside the default labs root directory you can use the `--allow-scattered` flag in the command.    Possible use case, you're running a side project and want everything related to the project are resided in one place.

When `--allow-scattered` is used, labkit will do the following before the default action above performed:

1. Adds the parent directory (e.g., `/tmp/experimental`) to `~/.config/labkit/config.yaml`
2. Ensures labkit list will discover this lab in the future

Executing the command in a directory out side the default labs root, in this case `/home/aprksy/workspace/sandbox/petstore/` should be:
```bash
(labkit) ➜  my-online-store ➜ labkit new petstore --allow-scattered
Added '/home/aprksy/workspace/sandbox' to lab search paths
[INFO] Created and entered directory: /home/aprksy/workspace/sandbox/petstore

# same with above ...

[OK] Lab initialized at /home/aprksy/workspace/sandbox/petstore
[INFO] Next: labkit node add <name>
[OK] Initialized empty lab 'petstore'
```
         
## Examples 
Basic Usage 
```bash
# Initialize lab structure in myapp-dev/. 
labkit init
```

Custom name
```bash
# Initialize lab structure in myapp-dev/ with name hiperf-lab. 
labkit init --name hiperf-lab
```
 
With Custom Template 
```bash
# Uses golden-api as base container template. 
labkit init --template golden-api
```
 
Scattered Mode (Opt-In Discovery) 
```bash
# Creates /tmp/sandbox/test-lab
# Adds /tmp/sandbox to global search paths
# Now labkit list will include labs in /tmp/sandbox/*
cd /tmp/sandbox/test-lab
labkit init --allow-scattered
```
Use sparingly. Encourages organization over sprawl. 
     
**Tips** 

    The lab name becomes the directory name and is used in lab.yaml
    You can edit lab.yaml after creation to change settings
    All generated files are Git-tracked automatically
     

See Also 

- labkit [`new`](new.md)  – Create new lab 
- labkit [`list`](list.md)  – Find all discoverable labs
     