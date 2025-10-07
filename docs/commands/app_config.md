# labkit Configuration System

`labkit` uses a layered configuration system to balance flexibility and predictability.

Settings are loaded from multiple sources, with later sources overriding earlier ones.

## Configuration Sources (Order of Precedence)

| Source | Purpose | Overrides |
|-------|--------|----------|
| 1. Default Values | Built-in defaults | Nothing |
| 2. Global Config File | User-wide settings (`~/.config/labkit/config.yaml`) | Defaults |
| 3. Environment Variables (`.env`) | Dynamic overrides (e.g., CI) | Global file |
| 4. Command-Line Flags | Per-command control | All above |

> 💡 Think: "Defaults → User Preferences → Session Override → Immediate Intent"

---

## 1. Default Values

If no other config exists, `labkit` uses:

```yaml
default_root: ~/workspace/labs
search_paths:
  - ~/workspace/labs

default_template: golden-base
user: $USER
```
These ensure labkit works out-of-the-box.

## 2. Global Config File 

Location: `~/.config/labkit/config.yaml` 

This file defines user-wide defaults. 

### Example 
```yaml
default_root: ~/workspace/labs
search_paths:
  - ~/workspace/labs
  - ~/clients/*/projects
  - /tmp/dev-labs

default_template: golden-dev-base
user: aprksy
```
> ✅ Supports shell-style glob patterns (*) for flexible scanning.

### Auto-Update via `--allow-scattered` 

When you run: 
```bash
labkit new myproject --allow-scattered
```

labkit automatically adds the parent directory (e.g., `~/sandbox`) to search_paths and saves the config. Now labkit list will discover labs in that location forever. 

To disable this behavior, omit `--allow-scattered`. 

## 3. Environment Variables (.env) 

You can override any global setting using environment variables. 

Create `.env` in your shell environment or project root: 
```bash
LABKIT_SEARCH_PATHS=~/workspace/labs,~/temp-experiments
LABKIT_DEFAULT_TEMPLATE=golden-api
LABKIT_USER=devuser
```

Supported `.env` Variables
| env var | config | type |
| --- | --- | --- |
| LABKIT_SEARCH_PATHS | search_paths | Comma-separated paths |
| LABKIT_DEFAULT_TEMPLATE | default_template | String |
| LABKIT_USER | user | String |
|

> ⚠️ .env is only read at startup — not monitored for changes.

## 4. Command-Line Flags 

Flags take precedence over all config sources. 
| flag | overrides |
| --- | --- |
| `--template <name>` | default_template |
| `--allow-scattered` | Adds to `search_paths` temporarily, then persists if used |
|

### Example: 
```bash
labkit new testapp --template golden-test
```
 
Uses golden-test even if `config.yaml` says golden-base. 

## Configuration Loading Flow
```text
Start
  │
  ▼
Load Default Values
  │
  ▼
Merge ~/.config/labkit/config.yaml
  │
  ▼
Apply .env overrides
  │
  ▼
Apply CLI flags (highest priority)
  │
  ▼
Final Runtime Config
```
All commands use this unified config object.

## Manual Config Management 
### View Current Config 

There’s no labkit config show yet, but you can inspect: 
```bash
cat ~/.config/labkit/config.yaml
```

Edit Manually:
```bash
mkdir -p ~/.config/labkit
nano ~/.config/labkit/config.yaml
```
Ensure valid YAML syntax.

Reset to Defaults:
```bash
rm ~/.config/labkit/config.yaml
```
Next command will regenerate structure on demand. 

### Best Practices 
| Goal | Recommendation |
| --- | --- |
| Keep labs organized | Use `~/workspace/labs` as primary location |
| Allow temporary labs | Use `--allow-scattered` sparingly |
| Share settings across tools | Use `.env` in project directories |
| Avoid config drift | Let labkit manage search_paths auto-add |
|
 
### See Also 

- labkit [`new`](new.md)  – Uses default_template, affects search_paths
- labkit [`list`](list.md)  – Scans all search_paths
- Environment Setup  – How to configure .env and templates
     

## ✅ Why This Matters

This document:
- Gives users control
- Explains surprising behavior (like auto-added paths)
- Empowers customization
- Serves as reference for future contributors

And it makes all other command docs simpler — they can just say:
> *“Uses the global `default_template` unless overridden.”*
