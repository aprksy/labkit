"""
This module purpose is to handle command line interface
"""

import argparse
from datetime import datetime
import json
import os
from pathlib import Path
import sys
import shutil
import glob
import yaml
from labkit.global_config import LabkitConfig

from .utils import container_exists, run, info, success, error, warning, fatal, heading, \
    BOLD, RESET
from .lab import Lab, list_templates

def main():
    """
    main: main loop for the program
    """
    parser = argparse.ArgumentParser(description="labkit - Incus lab manager")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # labkit new <name>
    prepare_cmd_new(subparsers)

    # labkit init
    prepare_cmd_init(subparsers)

    # labkit list
    prepare_cmd_list(subparsers)

    # labkit template
    prepare_cmd_template(subparsers)

    # labkit node add
    prepare_cmd_node(subparsers)

    # labkit requires
    prepare_cmd_requires(subparsers)

    # labkit up
    prepare_cmd_up(subparsers)

    # labkit down
    prepare_cmd_down(subparsers)

    args = parser.parse_args()
    if args.command == "new":
        cmd_new(args)
    elif args.command == "init":
        cmd_init(args)
    elif args.command == "list":
        cmd_list(args)
    elif args.command == "node":
        cmd_node(args)
    elif args.command == "requires":
        cmd_requires(args)
    elif args.command == "up":
        cmd_up(args)
    elif args.command == "down":
        cmd_down(args)
    elif args.command == "template":
        if args.action == "list":
            list_templates()

def prepare_cmd_new(subparsers):
    """
    prepare_cmd_node: prepares parser for subcommand and args for `new`
    """
    new_p = subparsers.add_parser("new", help="Create a new lab in a new directory")
    new_p.add_argument("name", help="Lab/project name")
    new_p.add_argument("--template", help="Override default template for nodes")
    new_p.add_argument("--allow-scattered", action="store_true",
                       help="Allow lab creation outside default labs root")
    new_p.add_argument("--force", "-f", action="store_true",
                       help="Overwrite existing directory")

def cmd_new(args):
    """
    cmd_new: handles 'new' command
    """
    config = LabkitConfig().load()  # Load global config
    current_dir = Path.cwd()

    if str(current_dir) != str(config.data["default_root"]):
        # If --allow-scattered, add parent dir to search_paths
        if getattr(args, "allow_scattered", False):
            if config.add_search_path(current_dir):
                config.save()  # Save updated config
                print(f"Added '{current_dir}' to lab search paths")
            else:
                print(f"'{current_dir}' already in search paths")
        else:
            error("Cannot create lab outside the default root.")
            info("If this is intentional, use flag --allow-scattered.")
            return

    check_passed = True
    project_dir = Path(args.name).absolute()
    if project_dir.exists():
        if not args.force:
            warning(f"Directory '{project_dir}' already exists. Use --force to overwrite.")
            return
        shutil.rmtree(project_dir)

    project_dir.mkdir(parents=True, exist_ok=True)
    os.chdir(project_dir)
    info(f"Created and entered directory: {project_dir}")

    # Run init logic
    cmd_init(argparse.Namespace(
        command="init",
        name=args.name,
        template=args.template or config.data["default_template"]
    ), check_passed)

def prepare_cmd_init(subparsers):
    """
    prepare_cmd_node: prepares parser for subcommand and args for `init`
    """
    init_p = subparsers.add_parser("init",
    help="Initialize current directory as a lab")
    init_p.add_argument("--name", type=str, help="Lab name")
    init_p.add_argument("--template", help="Set default node template")
    init_p.add_argument("--allow-scattered", action="store_true",
                        help="Allow lab creation outside default labs root")

def cmd_init(args, check_passed=False):
    """
    cmd_init: handles 'init' command
    """
    current_dir = Path.cwd()
    config = LabkitConfig().load()

    if (current_dir / "lab.yaml").exists():
        warning("This directory is already a lab (lab.yaml exists). Skipping init.")
        return

    if not check_passed:
        if str(current_dir.parent) != str(config.data["default_root"]):
            if getattr(args, "allow_scattered", False):
                parent_dir = current_dir.parent
                if config.add_search_path(parent_dir):
                    config.save()
                    print(f"Added '{parent_dir}' to global search paths")
            else:
                error("Cannot create lab outside the default root.")
                info("If this is intentional, use flag --allow-scattered.")
                return

    # Determine lab name
    lab_name = args.name or current_dir.name

    # Initialize lab structure
    lab = Lab.init(current_dir)
    lab.config["name"] = lab_name
    if hasattr(args, "template") and args.template:
        if not container_exists(args.template):
            warning(f"Template '{args.template}' not found. You may need to create it.")
        lab.config["template"] = args.template

    # Save updated config
    (current_dir / "lab.yaml").write_text(
        f"name: {lab_name}\n"
        f"template: {lab.config['template']}\n"
        f"user: {lab.config['user']}\n"
        "managed_by: labkit\n"
    )

    success(f"Initialized empty lab '{lab_name}'")

def prepare_cmd_node(subparsers):
    """
    prepare_cmd_node: prepares parser for subcommand and args for `node`
    """
    node_p = subparsers.add_parser("node", help="Manage nodes")
    node_sub = node_p.add_subparsers(dest="action", required=True)
    add_node_p = node_sub.add_parser("add", help="Add a new node")
    add_node_p.add_argument("name", help="Node/container name")
    add_node_p.add_argument("--template", help="Use specific template (overrides lab.yaml)")

    rm_node_p = node_sub.add_parser("rm", aliases=['del', 'remove', 'delete'],
                                    help="Remove a node")
    rm_node_p.add_argument("name", help="Node/container name")
    rm_node_p.add_argument("--force", action="store_true", help="Stop and delete if running")

    # In parser setup
    for subparser in [add_node_p, rm_node_p]:
        subparser.add_argument(
            "--dry-run", "-n",
            action="store_true",
            help="Show what would be done without applying changes"
        )

def cmd_node(args):
    """
    cmd_node: handles 'node' command
    """
    current_dir = Path.cwd()
    if not (current_dir / "lab.yaml").exists():
        error("This is not a lab directory. Run 'labkit init' first.")
        return

    try:
        lab = Lab(current_dir)
    except RuntimeError as e:
        fatal(f"Failed to load lab: {e}")
        return

    if args.action == "add":
        try:
            lab.add_node(args.name, template=args.template, dry_run=args.dry_run)
        except RuntimeError as e:
            error(f"Failed to add node: {e}")
    elif args.action in ["rm", "remove", "del", "delete"]:
        try:
            lab.remove_node(args.name, force=args.force, dry_run=args.dry_run)
        except RuntimeError as e:
            error(f"Failed to remove node: {e}")

def prepare_cmd_list(subparsers):
    """
    prepare_cmd_node: prepares parser for subcommand and args for `list`
    """
    list_p = subparsers.add_parser("list", help="List all labs in workspace")
    list_p.add_argument("--path", type=str, help="Search path (default: ~/workspace/labs)")
    list_p.add_argument("--format", choices=["table", "json"], default="table",
                        help="Output format")

def _process_root(root, labs, seen):
    parent_dir = [entry.path for entry in os.scandir(root) if entry.is_dir()]
    for p in parent_dir:
        p = Path(p)
        if not p.is_dir():
            continue
        if p in seen:
            continue

        seen.add(p)
        lab_yaml = p / "lab.yaml"
        if lab_yaml.exists():
            try:
                data = yaml.safe_load(lab_yaml.read_text()) or {}
                name = data.get("name") or p.name
                # Count nodes
                nodes_dir = p / "nodes"
                node_count = len([d for d in nodes_dir.iterdir() if d.is_dir()]) \
                if nodes_dir.exists() else 0
                mtime = lab_yaml.stat().st_mtime
                labs.append({
                    "name": name,
                    "nodes": node_count,
                    "mtime": mtime,
                    "path": p,
                    "template": data.get("template", "unknown"),
                })
            except Exception as e:
                raise RuntimeError(f"Failed to read {p}: {e}") from e

def cmd_list(args):
    """
    cmd_list: handles 'list' command
    """

    config = LabkitConfig().load()
    labs = []
    seen_paths = set()

    for base_path in config.data["search_paths"]:
        if str(base_path) == "":
            continue

        # Support glob patterns like */projects
        candidates = (
            [base_path] if "*" not in str(base_path) else
            glob.glob(str(base_path))
        )

        for candidate in candidates:
            _process_root(candidate, labs, seen_paths)

    # Sort by mtime
    labs.sort(key=lambda x: x["mtime"], reverse=True)

    if args.format == "json":
        print(json.dumps(labs, default=str, indent=2))
    else:
        _print_table(labs)

def _print_table(labs):
    """
    _print_table: print in table format
    """

    heading(f"Labs found: {len(labs)}")

    headers = ["NAME", "NODES", "TEMPLATE", "LAST MODIFIED", "PATH"]
    rows = []
    now = datetime.now()

    def _ago(dt):
        diff = now - datetime.fromtimestamp(dt)
        if diff.days > 0:
            return f"{diff.days}d ago"
        if diff.seconds > 3600:
            return f"{diff.seconds//3600}h ago"
        if diff.seconds > 60:
            return f"{diff.seconds//60}m ago"
        return "now"

    for lab in labs:
        rows.append([
            lab["name"],
            str(lab["nodes"]),
            lab["template"],
            _ago(lab["mtime"]),
            str(lab["path"])
        ])

    # Calculate max width for each column
    col_widths = [len(h) for h in headers]
    total_width = 0
    for row in rows:
        for i, cell in enumerate(row):
            col_widths[i] = max(col_widths[i], len(str(cell)))
            total_width += col_widths[i]

    # Format and print
    fmt = "  ".join(f"{{:<{w}}}" for w in col_widths)
    print(BOLD + fmt.format(*headers) + RESET)
    for row in rows:
        print(fmt.format(*row))

    print()

def prepare_cmd_requires(subparsers):
    """
    prepare_cmd_requires: prepare args for cnd_requires
    """
    req_p = subparsers.add_parser("requires", help="Manage external node dependencies")
    req_sub = req_p.add_subparsers(dest="req_action", required=True)

    req_sub.add_parser("list", help="List all required external nodes")
    req_sub.add_parser("check", help="Check if all required nodes are running")

    req_add_p = req_sub.add_parser("add", help="Declare that this lab requires a shared node")
    req_add_p.add_argument("names", nargs="+", help="Node names to require")

    req_rm_p = req_sub.add_parser("rm", aliases=['del', 'remove', 'delete'],
                                  help="Remove requirement for a shared node")
    req_rm_p.add_argument("names", nargs="+", help="Node names to unrequire")

    for subparser in [req_add_p, req_rm_p]:
        subparser.add_argument(
            "--dry-run", "-n",
            action="store_true",
            help="Show what would be done without applying changes"
        )

def cmd_requires(args):
    """
    cmd_requires: handles 'requires' command
    """
    current_dir = Path.cwd()
    lab_yaml = current_dir / "lab.yaml"
    if not lab_yaml.exists():
        fatal("This is not a lab directory. Run 'labkit init' first.")
        return

    try:
        lab = Lab(current_dir)
    except RuntimeError as e:
        error(f"Failed to load lab: {e}")
        return

    match args.req_action:
        case "add":
            try:
                lab.add_requirement(args.names, args.dry_run)
            except RuntimeError as e:
                error(f"Failed to add required node: {e}")
                return

        case "rm" | "remove" | "del" | "delete":
            try:
                lab.remove_requirement(args.names, args.dry_run)
            except RuntimeError as e:
                error(f"Failed to remove required node: {e}")
                return

        case "list":
            requires = lab.config.get("requires_nodes", [])
            if requires:
                print("This lab requires:")
                for n in sorted(requires):
                    print(f"  - {n}")
            else:
                info("No external node requirements declared")
        case "check":
            result = run(["incus", "list", "--format=json"], silent=True)
            containers = json.loads(result.stdout)
            running = {c["name"] for c in containers if c["status"] == "Running"}
            missing = [n for n in lab.config.get("requires_nodes", []) if n not in running]
            if missing:
                error(f"Required nodes not running: {', '.join(missing)}")
                sys.exit(1)
            else:
                success("All required nodes are running")

def prepare_cmd_up(subparsers):
    """
    prepare_cmd_up: prepare parser & subparser for cmd_up
    """
    up_p = subparsers.add_parser("up", help="Start all managed nodes within the lab")
    up_p.add_argument("--only",
                      help="Only start specific nodes (comma-separated, e.g. web01,db01)")
    up_p.add_argument("--no-deps", action="store_true",
                      help="Don't start required_nodes dependencies")

    for subparser in [up_p]:
        subparser.add_argument(
            "--dry-run", "-n",
            action="store_true",
            help="Show what would be done without applying changes"
        )

def cmd_up(args):
    """
    cmd_up: handles 'up' command
    """
    current_dir = Path.cwd()
    if not (current_dir / "lab.yaml").exists():
        fatal("This is not a lab directory. Run 'labkit init' first.")
        return

    try:
        lab = Lab(current_dir)
    except RuntimeError as e:
        error(f"Failed to load lab: {e}")
        return

    try:
        lab.up(
            only=args.only,
            include_deps=not args.no_deps,
            dry_run=args.dry_run
        )
    except RuntimeError as e:
        error(f"Failed to start-up lab: {e}")
        return

def prepare_cmd_down(subparsers):
    """
    prepare_cmd_down: prepare parser & subparser for cmd_down
    """
    down_p = subparsers.add_parser("down", help="Stop all managed nodes within the lab")
    down_p.add_argument("--only",
                        help="Only stop specific nodes (comma-separated, e.g. web01,db01)")
    down_p.add_argument("--suspend-required", action="store_true",
                        help="Suspend all required nodes (currently not implemented)")
    down_p.add_argument("--force-stop-all", action="store_true",
                        help="Stop all running nodes (currently not implemented)")

    # In parser setup
    for subparser in [down_p]:
        subparser.add_argument(
            "--dry-run", "-n",
            action="store_true",
            help="Show what would be done without applying changes"
        )

def cmd_down(args):
    """
    cmd_down: handles 'down' command
    """
    current_dir = Path.cwd()
    if not (current_dir / "lab.yaml").exists():
        fatal("This is not a lab directory. Run 'labkit init' first.")
        return

    try:
        lab = Lab(current_dir)
    except RuntimeError as e:
        error(f"Failed to load lab: {e}")
        return

    try:
        lab.down(
            only=args.only,
            suspend_required=args.suspend_required,
            force_stop_all=args.force_stop_all,
            dry_run=args.dry_run
        )
    except RuntimeError as e:
        error(f"Failed to shutdown lab: {e}")
        return

def prepare_cmd_template(subparsers):
    """
    prepare_cmd_node: prepares parser for subcommand and args for `template`
    """
    template_p = subparsers.add_parser("template",
                                       help="Initialize current directory as a lab")
    template_sub = template_p.add_subparsers(dest="action", required=True)
    template_sub.add_parser("list", help="List node templates")
