import argparse
from pathlib import Path
from .lab import Lab, list_templates

def main():
    parser = argparse.ArgumentParser(description="labkit - Incus lab manager")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # labkit init
    init_p = subparsers.add_parser("init", help="Initialize current directory as a lab")
    init_p.add_argument("--name", type=str, help="Lab name")

    # labkit template
    template_p = subparsers.add_parser("template", help="Initialize current directory as a lab")
    template_sub = template_p.add_subparsers(dest="action", required=True)
    template_sub.add_parser("list", help="List node templates")

    # labkit node add
    node_p = subparsers.add_parser("node", help="Manage nodes")
    node_sub = node_p.add_subparsers(dest="action", required=True)
    add_p = node_sub.add_parser("add", help="Add a new node")
    add_p.add_argument("name", help="Node/container name")
    add_p.add_argument("--template", help="Use specific template (overrides lab.yaml)")

    rm_p = node_sub.add_parser("rm", help="Remove a node")
    rm_p.add_argument("name", help="Node/container name")
    rm_p.add_argument("--force", action="store_true", help="Stop and delete if running")

    

    args = parser.parse_args()

    current_dir = Path.cwd()

    if args.command == "init":
        lab = Lab.init(current_dir)
        if args.name:
            lab.config["name"] = args.name
            (current_dir / "lab.yaml").write_text(
                f"name: {args.name}\n"
                "template: golden-image  # edit to change default\n"
            )

    elif args.command == "node":
        if not (current_dir / "lab.yaml").exists():
            print("❌ This is not a lab directory. Run 'labkit init' first.")
            return
        lab = Lab(current_dir)
        if args.action == "add":
            lab.add_node(args.name, template=args.template)
        elif args.action == "rm":
            lab.remove_node(args.name, force=args.force)

    elif args.command == "template":
        if args.action == "list":
            list_templates()
    
