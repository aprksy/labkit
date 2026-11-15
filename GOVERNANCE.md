# GOVERNANCE.md

Operating rules for this repository. **Read this before changing anything** — it is written for
both humans and AI agents, and the agent rules are binding.

---

## Machines

| Name | Address | Access | Role |
|---|---|---|---|
| `ocisrv` | `10.0.10.7` | `ssh ocisrv` | **Default dev host.** Code, light CI, light serving, small test runs. Also production — do not saturate |
| `sxi-work` | `10.0.10.2` | `ssh sxi-work` (port 2022) | **Heavy lane.** Heavy builds, cross-compile, anything device- or CPU-bound. Work queues here rather than moving back |
| `main-vnic` | `10.0.10.1` | local | WireGuard hub, LLM gateway. **Infra only — no clones** |
| `phone` | `10.0.10.5` | `ssh phone` | Field node (proot Ubuntu in Termux) |

- Refer to a machine by name, not by IP: "verified on `ocisrv`", not "10.10.10.7".
- Work starts on `ocisrv`; work that needs a real Incus daemon or a heavy build waits for the host
  that has it. Never claim a backend works because the code was imported — see *Verification gates*.
- `main-vnic` is not a workspace.

---

## What this repo is

`labkit` is a Python CLI (`labkit`, entry point `labkit.cli:main`) that turns a declarative lab
description into Incus containers and VMs, with git-versioned documentation, dependency tracking and
pluggable hooks.

| Path | Meaning |
|---|---|
| `labkit/` | core package: `cli.py`, `lab.py`, `models.py`, `config*.py`, `action_builder.py`, `action_executor.py` |
| `labkit/backends/` | `base.py` interface plus `incus.py`, `docker.py`, `qemu.py` |
| `labkit/plugin_infra/` | interfaces, plugin manager, timer, fs writer for plugins |
| `plugins/` | shipped plugins (`firstboot-handler`, `incus-event*`, `ssh-config`) and examples |
| `docs/commands/` | one page per CLI command; `docs/incus-setup.md` for host prerequisites |
| `contrib/` | systemd and openrc units for host-side helpers |
| `examples/` | runnable lab definitions |
| `CONFIG_FIELDS.md` | every config key, with meaning and default |

## Source of truth

When documents and code disagree, precedence is:

1. **`labkit/`** — the code and its `--help` output are what actually runs.
2. **`docs/commands/*.md`** — the documented behaviour of each command.
3. **`CONFIG_FIELDS.md`** — config keys, defaults and validation.
4. **`README.md`** — orientation only.

A command that behaves differently from `docs/commands/<command>.md` is a defect in one of the two,
fixed in the same PR. A new config key lands in `CONFIG_FIELDS.md` in the change that introduces it.

## Spec discipline

Milestones, not features. The `/speckit.*` commands in `.opencode/commands/` drive this flow:

- `.specify/memory/constitution.md` — the invariants this repo must never break. Amended by PR only.
- `specs/<nnn>-<slug>/spec.md` — one spec per slice: problem, scope, invariants touched, and
  acceptance a test could fail. `plan.md` and `tasks.md` sit beside it.
- The task list is the issue list: one issue per task, each carrying its acceptance line.
- A slice closes when every task issue is closed and the PRs that closed them demonstrate the
  acceptance. Update `STATUS.md` (or the spec's own status line) when it closes.
- `.specify/memory/current-state.md` is an agent-written half page that `/speckit.specify` reads
  instead of guessing at the tree. Reviewed by exception; never treated as approved documentation.

## Worktrees

Worktrees live **inside the project directory**, never loose in `$HOME`:

- `.slim/worktrees/<lane>` — lanes owned by the `slim` tooling
- `.worktree/<name>` — ad-hoc workspace for a task or an agent

Both are git-ignored. A worktree at `~/<project>-<task>` is a review blocker: it hides the branch
from `git worktree list` and outlives the PR that created it.

- Remove the worktree in the same pass that merges its branch.
- Never leave uncommitted work in a worktree.
- `/tmp/labkit-*` is fine for throwaway verification clones.

## Branching

```
master      release line, repository default; promotion-only, always installable
dev         integration branch; feature work lands here first
feat/<topic>  fix/<topic>  chore/<topic>  docs/<topic>  refactor/<topic>   short-lived, one concern
```

- **Never commit directly to `master`.** Feature PRs target `dev`; `master` moves only by a
  promotion PR from `dev`.
- The long-lived branch is **`dev`** — not `development`, not `develop`.
- **`dev` must contain every commit on `master`.** If something lands on `master` without passing
  through `dev`, reconcile `master` back into `dev` in its own PR rather than letting the two drift.
- Branch names are lower-case and hyphenated; no dots.
- Delete a topic branch once merged. The historical `refactor` branch is dead — do not revive it.
- The remote is `github.com/aprksy/labkit` (public). Do not create another.

## Commits

Conventional Commits, imperative mood, subject ≤ 72 characters:

```
feat(backends): qemu backend honours memory limits
fix(cli): `labkit down` no longer removes unknown nodes
docs(commands): document `node-rm --force`
```

Prefixes: `feat` `fix` `chore` `docs` `refactor` `test` `perf` `build` `ci`.

Explain **why** in the body when the change is not self-evident. One logical change per commit.

## Pull requests

- One concern per PR. If it cannot be described in one sentence, split it.
- The body states **what changed** and **how it was verified** — the command and its real output,
  never "should work".
- `dev` → `master` promotions are reviewed and merged by the owner.

## Issues and provenance

Issues are the queue of record.

1. **Issue before branch.** Branch as `issue-<n>-<concern>`, or a conventional `feat/*` name when no
   issue applies.
2. **Traceability marker** in every PR body:

       Issue: #<n> | <refs|advances|closes|none>

3. **Human merge.** The agent never merges its own work.

## Verification gates

Run these before opening a PR; paste the result in the body.

| Gate | Command | State at import (2026-11-15) |
|---|---|---|
| install | `uv sync --group dev` | works |
| lint (fast) | `uv run ruff check .` | **95 findings** (76 auto-fixable) — do not add more |
| lint (scored) | `uv run pylint labkit` | **7.81/10**; the README badge says 9.79, so the badge is stale |
| package | `uv build` | produces `dist/labkit-<ver>-py3-none-any.whl` and sdist |
| CLI | `uv run labkit --help` | works |
| tests | — | **none exist**; there is no test suite in this repo |

- A gate that cannot run must be reported as not run. Never present an import as a verification.
- Anything touching a backend needs a real daemon check on a host that has that daemon, or an
  explicit "not verified against a live daemon" sentence in the PR body.
- Closing the test-suite gap (`tests/` with pytest, wired into `make test`) is the first quality
  milestone; until then `ruff` and `pylint` are the only automated guards.

## Release

- Version lives in `pyproject.toml` (`[project].version`); current line is `0.2.0`.
- Bump on `dev`, promote with a `dev` → `master` PR, then create an **annotated** tag on `master`:
  `git tag -a v0.2.0 -m "labkit 0.2.0" && git push origin v0.2.0`.
- Assert `git rev-list --count dev..master` prints `0` before tagging.
- The repo has **no tags yet** — the first tag must be cut from `master` at the promotion that
  matches the version in `pyproject.toml`.
- Release notes list breaking changes; this tool takes its own labs seriously and breaking a lab
  format requires a `migrate` path (see the README's breaking-changes section).

## Plugins

- A plugin is a directory with `plugin.yaml` plus `plugin.py`, loaded by `plugin_infra`.
- A plugin talks to the core only through `plugin_infra/interfaces.py`. Importing core internals
  from a plugin is a review blocker.
- Shipped plugins follow the same contract as user plugins; they get no private back door.
- Every plugin documents the hooks it implements and whether it is safe to run twice.

## Data, secrets, safety

- No secrets, keys, tokens or `.env` files in the repo or in a diff. Config that needs a secret
  names an environment variable instead of holding a value.
- Lab state is generated at runtime (`labkit/lab.py`), not committed. Do not commit generated lab
  directories, `.venv/`, `dist/` or build caches.
- Destructive operations require an explicit flag and must name what they destroy; a command never
  deletes a container, VM or node it was not asked about.
- When in doubt about a host, stop and ask the owner. `ocisrv` also runs production services.

## Agent rules (binding)

1. Never commit directly to `dev` or `master`; work on a topic branch and open a PR against `dev`.
2. Never merge your own PR, and never tag a release.
3. Do not claim a backend, a command or a plugin works unless you ran it and pasted the output.
4. Do not silence a gate by editing its configuration; fix the finding or report it.
5. Keep `docs/commands/` and `CONFIG_FIELDS.md` in sync with code in the same PR.
6. Do not rewrite history on `dev` or `master` (no force-push, no rebase of published commits).
7. Do not add a dependency without a reason in the PR body.
