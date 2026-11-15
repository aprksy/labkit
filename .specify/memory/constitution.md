# labkit Constitution

The invariants this repository must never break. A change that violates one is rejected, not
negotiated. Amend only by PR against `dev`, with the reason in the commit body.

## Core Principles

### I. One backend contract
Every backend implements `labkit/backends/base.py` and is selected by configuration. A backend may
not be special-cased in the CLI, in `lab.py` or in an action; if a backend needs different
behaviour, the interface grows for all backends.

### II. Declarative labs, convergent actions
A lab is described by its own files. What runs is decided from that description, never from what
happens to exist on the host. `up` and `down` converge towards the declared state and are safe to
re-run; they do not "remember" a previous run.

### III. Destructive actions are named and gated
A command that removes, recreates or overwrites a container, VM, node or file must (a) name exactly
what it will destroy, (b) require an explicit flag or confirmation for the destructive path, and
(c) never act on an object the user did not name. "Clean up everything" is not an acceptable
implementation of a delete command.

### IV. Plugins are guests
A plugin talks to the core only through `labkit/plugin_infra/interfaces.py`. Shipped plugins obey
the same contract as user plugins and get no private access to core internals. A plugin declares its
hooks in `plugin.yaml` and documents whether it is safe to run twice.

### V. Documentation travels with the command
`docs/commands/<command>.md` and `CONFIG_FIELDS.md` are updated in the same PR that changes a
command's behaviour or a config key. A stale command page is a defect. The `--help` text, the docs
page and the code do not disagree at merge time.

## Quality gates

- `uv run ruff check .` and `uv run pylint labkit` must not get worse in a PR; new code arrives
  clean.
- `uv build` must produce a wheel and sdist.
- There is **no test suite yet**. That is a known gap, not a permitted state: the first milestone
  that adds Python logic adds `tests/` with pytest for it, and `make test` (or `uv run pytest`) in
  the verification section of every PR from then on.
- A gate that could not run is reported as not run. Never as passed.

## Amendment

A principle changes by a PR against `dev` that edits this file, states which principle and why, and
updates any document that quoted it. Historical reasoning stays in the git history; old versions are
never rewritten.
