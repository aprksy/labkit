# labkit — current state

Written by an agent on 2026-11-15 from the tree at `dev` `14c1a6de`, on `ocisrv` (aarch64, OL9).
`/speckit.specify` reads this instead of guessing. It is a snapshot, not a spec, and it is wrong the
moment someone changes the CLI — update it in the PR that changes behaviour.

## Entry points

- Console script `labkit` → `labkit.cli:main` (declared in `[project.scripts]`).
- Commands, from `uv run labkit --help`: `new`, `init`, `list`, `template`, `node`, `requires`, `up`,
  `down`, `migrate`. Sub-commands live under `node` (`add`/`rm`) and `requires` (`add`/`rm`).
- Backends: `labkit/backends/{incus,docker,qemu}.py` behind the interface in `backends/base.py`;
  selected by config, not by CLI flag.
- Plugins: `plugins/*/plugin.yaml` + `plugin.py`, loaded through `labkit/plugin_infra/`.

## Verify (measured this session)

| Command | Result |
|---|---|
| `uv sync --group dev` | resolves; runtime deps are `PyYAML`, `dotenv`; dev group is `pylint`, `ruff` |
| `uv run labkit --help` | exits 0, lists the nine commands above |
| `uv run ruff check .` | 95 findings, 76 fixable |
| `uv run pylint labkit` | 7.81/10 |
| `uv build` | `dist/labkit-0.2.0-py3-none-any.whl` + `labkit-0.2.0.tar.gz` |
| `uv run pytest` | no test suite exists |

## Traps

- The README badge claims pylint **9.79/10**; the tree scores **7.81/10**. The badge is stale — do not
  cite it as evidence.
- `labkit --help` describes `template` as "Initialize current directory as a lab", a copy of `init`'s
  text. Read `labkit/cli.py` before documenting or changing `template`.
- Version `0.2.0` in `pyproject.toml` has **no tag** in the repo; releases start with the first
  promotion to `master`.
- `master` (default) and `dev` had diverged before import — `master` carried 19 `Merge pull request
  #N from aprksy/dev` commits that `dev` lacked, `dev` carried 6 refactor commits from PRs #32/#33.
  Reconcile PR merges `master` into `dev`, conflict-free.
- No pytest, no `Makefile`, no CI workflow: `ruff` and `pylint` are the only automated guards today.
- `labkit/plugin_infra/` and `labkit/plugin_manager.py` both exist; the former is what the plugin
  contract is written against. Check which one a code path uses before editing the other.
