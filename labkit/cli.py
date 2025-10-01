import argparse
from datetime import datetime
import json
from logging import error, warning
import os
from pathlib import Path

import yaml

from labkit.utils import container_exists, info, success, warning, error, fatal, heading
from .lab import Lab, list_templates

def main():
    parser = argparse.ArgumentParser(description="labkit - Incus lab manager")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # labkit new <name>
    new_p = subparsers.add_parser("new", help="Create a new lab in a new directory")
    new_p.add_argument("name", help="Lab/project name")
    new_p.add_argument("--template", help="Override default template for nodes")
    new_p.add_argument("--force", "-f", action="store_true", help="Overwrite existing directory")

    # labkit init
    init_p = subparsers.add_parser("init", help="Initialize current directory as a lab")
    init_p.add_argument("--name", type=str, help="Lab name")
    init_p.add_argument("--template", help="Set default node template")

    # labkit list
    list_p = subparsers.add_parser("list", help="List all labs in workspace")
    list_p.add_argument("--path", type=str, help="Search path (default: ~/workspace/labs)")
    list_p.add_argument("--format", choices=["table", "json"], default="table", help="Output format")

    # labkit template
    template_p = subparsers.add_parser("template", help="Initialize current directory as a lab")
    template_sub = template_p.add_subparsers(dest="action", required=True)
    template_sub.add_parser("list", help="List node templates")

    # labkit node add
    node_p = subparsers.add_parser("node", help="Manage nodes")
    node_sub = node_p.add_subparsers(dest="action", required=True)
    add_node_p = node_sub.add_parser("add", help="Add a new node")
    add_node_p.add_argument("name", help="Node/container name")
    add_node_p.add_argument("--template", help="Use specific template (overrides lab.yaml)")

    rm_node_p = node_sub.add_parser("rm", aliases=['del', 'remove', 'delete'], help="Remove a node")
    rm_node_p.add_argument("name", help="Node/container name")
    rm_node_p.add_argument("--force", action="store_true", help="Stop and delete if running")

    # labkit requires
    req_p = subparsers.add_parser("requires", help="Manage external node dependencies")
    req_sub = req_p.add_subparsers(dest="req_action", required=True)

    req_add_p = req_sub.add_parser("add", help="Declare that this lab requires a shared node")
    req_add_p.add_argument("names", nargs="+", help="Node names to require")

    req_rm_p = req_sub.add_parser("rm", aliases=['del', 'remove', 'delete'], help="Remove requirement for a shared node")
    req_rm_p.add_argument("names", nargs="+", help="Node names to unrequire")

    list_p = req_sub.add_parser("list", help="List all required external nodes")
    req_sub.add_parser("check", help="Check if all required nodes are running")

    # labkit up
    up_p = subparsers.add_parser("up", help="Start all managed nodes within the lab")

    # labkit down
    down_p = subparsers.add_parser("down", help="Stop all managed nodes within the lab")

    # In parser setup
    for subparser in [up_p, down_p, add_node_p, rm_node_p, req_add_p, req_rm_p]:
        subparser.add_argument(
            "--dry-run", "-n",
            action="store_true",
            help="Show what would be done without applying changes"
        )    

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
    
def cmd_new(args):
    project_dir = Path(args.name).absolute()

    if project_dir.exists():
        if not args.force:
            warning(f"Directory '{project_dir}' already exists. Use --force to overwrite.")
            return
        import shutil
        shutil.rmtree(project_dir)

    project_dir.mkdir(parents=True, exist_ok=args.force)
    os.chdir(project_dir)

    info(f"Created and entered directory: {project_dir}")

    # Reuse init logic
    cmd_init(argparse.Namespace(
        command="init",
        name=args.name,
        template=args.template or "golden-base"
    ))

def cmd_init(args):
    current_dir = Path.cwd()

    if (current_dir / "lab.yaml").exists():
        warning(f"This directory is already a lab (lab.yaml exists). Skipping init.")
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

    from .utils import success
    success(f"Initialized empty lab '{lab_name}'")

def cmd_node(args):
    current_dir = Path.cwd()
    if not (current_dir / "lab.yaml").exists():
        error("This is not a lab directory. Run 'labkit init' first.")
        return

    try:
        lab = Lab(current_dir)
    except Exception as e:
        fatal(f"Failed to load lab: {e}")
        return

    if args.action == "add":
        try:
            lab.add_node(args.name, template=args.template, dry_run=args.dry_run)
        except Exception as e:
            error(f"Failed to add node: {e}")
    elif args.action in ["rm", "remove", "del", "delete"]:
        try:
            lab.remove_node(args.name, force=args.force, dry_run=args.dry_run)
        except Exception as e:
            error(f"Failed to remove node: {e}")

def cmd_list(args):
    import os
    from pathlib import Path
    from datetime import datetime

    # Determine search path
    search_path_str = args.path or os.path.expanduser("~/workspace/labs")
    search_path = Path(search_path_str)

    if not search_path.is_dir():
        fatal(f"Search path not found: {search_path}")
        return

    labs = []

    # Walk directories looking for lab.yaml
    for item in search_path.iterdir():
        if not item.is_dir():
            continue
        lab_yaml = item / "lab.yaml"
        if not lab_yaml.exists():
            continue

        try:
            config = yaml.safe_load(lab_yaml.read_text()) or {}
            name = config.get("name") or item.name

            # Count nodes
            nodes_dir = item / "nodes"
            node_count = len([d for d in nodes_dir.iterdir() if d.is_dir()]) if nodes_dir.exists() else 0

            template = config.get("template", "unknown")
            mtime = datetime.fromtimestamp(lab_yaml.stat().st_mtime)
            relative_path = f"~/{item.relative_to(Path.home())}" if item.is_relative_to(Path.home()) else str(item)

            labs.append({
                "name": name,
                "nodes": node_count,
                "template": template,
                "mtime": mtime,
                "path": relative_path,
                "full_path": item,
            })
        except Exception as e:
            error(f"Failed to read lab {item}: {e}")

    if not labs:
        error(f"No labs found in {search_path}")
        info("Create one with: labkit new <project-name>")
        return

    # Sort by modification time (newest first)
    labs.sort(key=lambda x: x["mtime"], reverse=True)

    if args.format == "json":
        import json as std_json
        print(std_json.dumps(labs, indent=2, default=str))
    else:
        _print_table(labs)

def _print_table(labs):
    from .utils import BOLD, RESET

    heading(f"\nLabs found:\n")

    headers = ["NAME", "NODES", "TEMPLATE", "LAST MODIFIED", "PATH"]
    rows = []
    now = datetime.now()

    def _ago(dt):
        diff = now - dt
        if diff.days > 0:
            return f"{diff.days}d ago"
        elif diff.seconds > 3600:
            return f"{diff.seconds//3600}h ago"
        elif diff.seconds > 60:
            return f"{diff.seconds//60}m ago"
        else:
            return "now"

    for lab in labs:
        rows.append([
            lab["name"],
            str(lab["nodes"]),
            lab["template"],
            _ago(lab["mtime"]),
            lab["path"]
        ])

    # Calculate max width for each column
    col_widths = [len(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            col_widths[i] = max(col_widths[i], len(cell))

    # Format and print
    fmt = "  ".join(f"{{:<{w}}}" for w in col_widths)
    print(fmt.format(*[BOLD + h + RESET for h in headers]))
    for row in rows:
        print(fmt.format(*row))

    print()

def cmd_requires(args):
    current_dir = Path.cwd()
    lab_yaml = current_dir / "lab.yaml"
    if not lab_yaml.exists():
        fatal("This is not a lab directory. Run 'labkit init' first.")
        return

    try:
        lab = Lab(current_dir)
    except Exception as e:
        error(f"Failed to load lab: {e}")
        return

    if args.req_action == "add":
        try:
            lab.add_requirement(args.names, args.dry_run)
        except Exception as e:
            error(f"Failed to add required node: {e}")
            return
    elif args.req_action in ["rm", "remove", "del", "delete"]:
        try:
            lab.remove_requirement(args.names, args.dry_run)
        except Exception as e:
            error(f"Failed to remove required node: {e}")
            return
    elif args.req_action == "list":
        requires = lab.config.get("requires_nodes", [])
        if requires:
            print("This lab requires:")
            for n in sorted(requires):
                print(f"  - {n}")
        else:
            info("No external node requirements declared")
    elif args.req_action == "check":
        from .utils import run, success, error
        result = run(["incus", "list", "--format=json"], silent=True)
        containers = json.loads(result.stdout)
        running = {c["name"] for c in containers if c["status"] == "Running"}
        missing = [n for n in lab.config.get("requires_nodes", []) if n not in running]
        if missing:
            error(f"Required nodes not running: {', '.join(missing)}")
            exit(1)
        else:
            success("All required nodes are running")
    elif args.req_action == "list":
        if requires:
            print("This lab requires:")
            for n in sorted(requires):
                print(f"  - {n}")
        else:
            info("No external node requirements declared")
        return
    elif args.req_action == "check":
        from .utils import run
        result = run(["incus", "list", "--format=json"], silent=True)
        containers = json.loads(result.stdout)
        running = {c["name"] for c in containers if c["status"] == "Running"}
        missing = [n for n in requires if n not in running]
        if missing:
            error(f"Required nodes not running: {', '.join(missing)}")
            exit(1)
        else:
            success("All required nodes are running")
        return

def cmd_up(args):
    current_dir = Path.cwd()
    if not (current_dir / "lab.yaml").exists():
        fatal("This is not a lab directory. Run 'labkit init' first.")
        return

    try:
        lab = Lab(current_dir)
    except Exception as e:
        error(f"Failed to load lab: {e}")
        return

    try:
        lab.up(dry_run=args.dry_run)
    except Exception as e:
        error(f"Failed to start-up lab: {e}")
        return

def cmd_down(args):
    current_dir = Path.cwd()
    if not (current_dir / "lab.yaml").exists():
        fatal("This is not a lab directory. Run 'labkit init' first.")
        return

    try:
        lab = Lab(current_dir)
    except Exception as e:
        error(f"Failed to load lab: {e}")
        return
    
    try:
        lab.down(dry_run=args.dry_run)
    except Exception as e:
        error(f"Failed to shutdown lab: {e}")
        return
    