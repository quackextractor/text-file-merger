from typing import List


def generate_tree(tasks, source_dir: str) -> str:
    """Generates a text-based directory tree representation from the pre-collected tasks.

    Builds a nested dictionary representation and formats it using Unicode box characters.
    """
    tree = {}
    for task in tasks:
        # tasks are classified with display_name already formatted with forward slashes
        parts = task.display_name.split("/")
        current = tree
        for part in parts:
            if not part:
                continue
            if part not in current:
                current[part] = {}
            current = current[part]

    lines = []

    def recurse(node, prefix=""):
        keys = sorted(node.keys())
        for i, key in enumerate(keys):
            is_last = (i == len(keys) - 1)
            connector = "└── " if is_last else "├── "
            lines.append(f"{prefix}{connector}{key}")

            next_prefix = prefix + ("    " if is_last else "│   ")
            recurse(node[key], next_prefix)

    recurse(tree)
    return "\n".join(lines)
