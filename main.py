#!/usr/bin/env python3
"""
treer - CLI tool to create, display, and theme directory trees.

Usage:
  treer create "New folder\n│   ├── bot.py\n│   └── requirements.txt"
  treer create --file myproject.tree
  treer scan [path]
  treer theme --style emoji [tree_string]
  treer theme --style plain [tree_string]
  treer theme --file myproject.tree --style nerd
"""

import os
import sys
import argparse
import re

# ─── Tree characters ────────────────────────────────────────────────────────

TREE_CHARS = ("│", "├", "└", "─", "┬")

# ─── Themes ─────────────────────────────────────────────────────────────────

# Each theme: dict with 'folder' and a callable get_file(name) -> icon
THEMES = {
    "plain": {
        "folder": "",
        "file": "",
        "desc": "No icons — clean ASCII tree",
    },
    "emoji": {
        "folder": "📁 ",
        "file": "📄 ",
        "desc": "Emoji icons for folders and files",
        "ext": {
            ".py":   "🐍 ", ".js": "🟨 ", ".ts": "🔷 ",
            ".json": "📋 ", ".md": "📝 ", ".txt": "📝 ",
            ".html": "🌐 ", ".css": "🎨 ", ".sh":  "⚙️  ",
            ".env":  "🔒 ", ".yml":"⚙️  ", ".yaml":"⚙️  ",
            ".png":  "🖼️  ", ".jpg":"🖼️  ", ".svg": "🎭 ",
            ".zip":  "📦 ", ".tar":"📦 ", ".git": "🐙 ",
            ".lock": "🔒 ", ".cfg": "⚙️  ", ".toml":"⚙️  ",
        },
    },
    "nerd": {
        "folder": " ",
        "file": " ",
        "desc": "Nerd Font icons (requires a patched font like JetBrainsMono Nerd Font)",
        "ext": {
            ".py":   " ", ".js":  " ", ".ts":   " ",
            ".json": " ", ".md":  " ", ".txt":  " ",
            ".html": " ", ".css": " ", ".sh":   " ",
            ".env":  " ", ".yml": " ", ".yaml": " ",
            ".png":  " ", ".jpg": " ", ".svg":  " ",
            ".zip":  " ", ".tar": " ", ".lock": " ",
            ".rs":   " ", ".go":  " ", ".c":    " ",
            ".cpp":  " ", ".rb":  " ", ".php":  " ",
            ".toml": " ", ".cfg": " ", ".ini":  " ",
        },
    },
    "minimal": {
        "folder": "+ ",
        "file": "· ",
        "desc": "Minimal ASCII-art style, no Unicode needed",
    },
    "retro": {
        "folder": "[DIR] ",
        "file": "[---] ",
        "desc": "Old-school DOS/terminal retro style",
        "ext": {
            ".py":  "[.py] ", ".js":  "[.js] ", ".ts":  "[.ts] ",
            ".json":"[JSN] ", ".md":  "[.md] ", ".txt": "[TXT] ",
            ".html":"[HTM] ", ".css": "[CSS] ", ".sh":  "[.sh] ",
            ".env": "[ENV] ", ".yml": "[YML] ", ".yaml":"[YML] ",
        },
    },
}


def get_icon(name: str, is_dir: bool, theme: dict) -> str:
    """Return the icon string for a file/dir under a given theme."""
    if is_dir:
        return theme.get("folder", "")
    ext = os.path.splitext(name)[1].lower()
    ext_map = theme.get("ext", {})
    return ext_map.get(ext, theme.get("file", ""))


# ─── Parser: tree string → list of (depth, name) ────────────────────────────

KNOWN_NO_EXT = {
    "Makefile", "Dockerfile", "Procfile", "Pipfile",
    "LICENSE", "LICENCE", "README", "CHANGELOG",
    ".gitignore", ".dockerignore", ".editorconfig",
    ".env", ".htaccess",
}


def _is_dir_guess(name: str, raw_line: str) -> bool:
    """Heuristic: is this entry a directory?"""
    if raw_line.rstrip().endswith("/"):
        return True
    bare = name.rstrip("/")
    if "." not in bare:
        return bare not in KNOWN_NO_EXT
    return False


def parse_tree(text: str):
    """
    Parse a tree string into a list of (depth, name, is_dir).

    Depth semantics:
      -  0  → root node (the first non-blank line with no tree connector)
      -  1  → direct children of root (lines starting with ├── / └── )
      -  2+ → deeper nesting (each "│   " or "    " block adds 1)
    """
    lines = text.splitlines()
    entries = []

    for line in lines:
        if not line.strip():
            continue

        # Match lines that have a tree connector: optional indent + (├ or └)── 
        m = re.match(r"^((?:[│ ]   )*)((?:├──|└──)─*\s*)(.*)", line)
        if m:
            indent_part, _connector, rest = m.groups()
            # depth = number of indent groups (each 4 chars) + 1 for the connector level
            depth = len(re.findall(r"[│ ]   ", indent_part)) + 1
            # strip any icons from rest (emoji, PUA, label tokens)
            name = _strip_name_icons(rest).strip().rstrip("/")
        else:
            # Root line — no connector prefix
            depth = 0
            name = _strip_name_icons(line).strip().rstrip("/")

        if not name:
            continue

        is_dir = _is_dir_guess(name, line)
        entries.append((depth, name, is_dir))

    return entries


def _strip_name_icons(s: str) -> str:
    """Remove icon prefixes from a name segment."""
    # Remove emoji (broad Unicode ranges)
    s = re.sub(r"[\U0001F300-\U0001FFFF\u2600-\u27FF][\uFE0F\u20E3]?\s*", "", s)
    # Remove PUA chars (nerd fonts)
    s = re.sub(r"[\uE000-\uF8FF\U000F0000-\U000FFFFF]\s*", "", s)
    # Remove retro labels like [DIR], [.py], [---]
    s = re.sub(r"\[[\w./\-]+\]\s*", "", s)
    # Remove minimal markers like "+ " "· "
    s = re.sub(r"^[+·]\s+", "", s)
    return s


# ─── CREATE: build files and folders from tree ───────────────────────────────

def create_from_tree(text: str, base: str = "."):
    """Create directories and files described by tree text."""
    entries = parse_tree(text)
    if not entries:
        print("⚠  No entries found — is the tree format correct?")
        return

    # depth_path[d] = absolute path of the last entry seen at depth d
    # depth -1 = the base directory passed by the user
    depth_path = {-1: os.path.abspath(base)}
    created = []

    for depth, name, is_dir in entries:
        parent_depth = depth - 1
        parent = depth_path.get(parent_depth, os.path.abspath(base))
        full_path = os.path.join(parent, name)

        if is_dir:
            os.makedirs(full_path, exist_ok=True)
            depth_path[depth] = full_path
            created.append(("dir", full_path))
        else:
            os.makedirs(parent, exist_ok=True)
            if not os.path.exists(full_path):
                open(full_path, "w").close()
            created.append(("file", full_path))

    print(f"✔  Created {len(created)} items under '{os.path.abspath(base)}':\n")
    for kind, path in created:
        icon = "📁" if kind == "dir" else "📄"
        rel = os.path.relpath(path, base)
        print(f"  {icon}  {rel}")


# ─── SCAN: directory → tree string ───────────────────────────────────────────

def scan_dir(root: str = ".", theme_name: str = "plain",
             ignore: list = None, max_depth: int = None):
    """Walk a directory and return a themed tree string."""
    if ignore is None:
        ignore = {".git", "__pycache__", "node_modules", ".venv",
                  "venv", ".DS_Store", ".idea", ".pytest_cache"}

    theme = THEMES.get(theme_name, THEMES["plain"])
    lines = [get_icon(os.path.basename(root), True, theme) + os.path.basename(root) or "."]

    def walk(path, prefix="", depth=0):
        if max_depth is not None and depth >= max_depth:
            return
        try:
            entries = sorted(os.scandir(path), key=lambda e: (not e.is_dir(), e.name))
        except PermissionError:
            return

        entries = [e for e in entries if e.name not in ignore]

        for i, entry in enumerate(entries):
            is_last = i == len(entries) - 1
            connector = "└── " if is_last else "├── "
            icon = get_icon(entry.name, entry.is_dir(), theme)
            lines.append(prefix + connector + icon + entry.name)

            if entry.is_dir():
                extension = "    " if is_last else "│   "
                walk(entry.path, prefix + extension, depth + 1)

    walk(root)
    return "\n".join(lines)


# ─── THEME: apply/strip icons from a tree string ────────────────────────────

def strip_icons(text: str) -> str:
    """Remove all icon prefixes from a tree (leaves pure structure)."""
    # Remove common emoji and nerd font icon patterns after tree chars
    # Emoji: chars in emoji range
    emoji_pattern = re.compile(
        r"((?:├── |└── |│   |    ))"
        r"(?:[\U0001F300-\U0001FFFF\u2600-\u27FF][\uFE0F\u20E3]?\s*)*",
        re.UNICODE,
    )
    # Also strip nerd-font single-char icons (Private Use Area)
    pua_pattern = re.compile(r"[\uE000-\uF8FF\U000F0000-\U000FFFFF]\s*")

    lines = []
    for line in text.splitlines():
        # Strip PUA (nerd fonts)
        line = pua_pattern.sub("", line)
        # Strip simple label tokens like [DIR], [---], [.py], + , · 
        line = re.sub(
            r"((?:├──|└──|│)\s+)(\[[\w./\-]+\]\s+|[+·]\s+)",
            r"\1",
            line,
        )
        lines.append(line)
    return "\n".join(lines)


def apply_theme(text: str, theme_name: str) -> str:
    """Strip existing icons and apply a new theme to a tree string."""
    theme = THEMES.get(theme_name)
    if not theme:
        print(f"Unknown theme '{theme_name}'. Available: {', '.join(THEMES)}")
        sys.exit(1)

    clean = strip_icons(text)
    out_lines = []

    for line in clean.splitlines():
        m = re.match(r"^((?:[│ ]   )*)((?:├── |└── ))(.*)", line)
        if m:
            indent, connector, name = m.groups()
            name = name.strip()
            # heuristic: has extension → file
            is_dir = "." not in name or name.endswith("/")
            icon = get_icon(name.rstrip("/"), is_dir, theme)
            out_lines.append(indent + connector + icon + name)
        else:
            # root line
            name = line.strip()
            icon = get_icon(name, True, theme)  # root is always a dir
            out_lines.append(icon + name)

    return "\n".join(out_lines)


# ─── CLI ─────────────────────────────────────────────────────────────────────

def read_input(args_text, args_file):
    """Read tree text from --file or inline argument."""
    if args_file:
        with open(args_file) as f:
            return f.read()
    if args_text:
        return "\n".join(args_text) if isinstance(args_text, list) else args_text
    # try stdin
    if not sys.stdin.isatty():
        return sys.stdin.read()
    return None


def cmd_create(args):
    text = read_input(args.tree, args.file)
    if not text:
        print("Error: provide a tree via argument or --file.")
        sys.exit(1)
    base = args.output or "."
    create_from_tree(text, base)


def cmd_scan(args):
    root = args.path or "."
    style = args.style or "plain"
    max_d = args.depth
    result = scan_dir(root, style, max_depth=max_d)
    print(result)
    if args.save:
        with open(args.save, "w") as f:
            f.write(result)
        print(f"\n💾  Saved to {args.save}")


def cmd_theme(args):
    text = read_input(args.tree, args.file)
    if not text:
        print("Error: provide a tree via argument or --file.")
        sys.exit(1)
    result = apply_theme(text, args.style)
    print(result)
    if args.save:
        with open(args.save, "w") as f:
            f.write(result)
        print(f"\n💾  Saved to {args.save}")


def cmd_themes(_args):
    """List available themes."""
    print("Available themes:\n")
    for name, info in THEMES.items():
        sample_folder = info.get("folder", "")
        sample_file   = info.get("file",   "")
        print(f"  {name:<10}  {info['desc']}")
        print(f"             folder: {sample_folder}my-project   "
              f"file: {sample_file}main.py\n")


def main():
    parser = argparse.ArgumentParser(
        prog="treer",
        description="🌲 treer — create, scan, and theme directory trees",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  treer create "my-app\\n├── main.py\\n└── requirements.txt"
  treer create --file project.tree --output ./workspace
  treer scan . --style emoji --depth 3
  treer scan . --style nerd --save mytree.tree
  treer theme --style emoji --file mytree.tree
  treer theme --style plain "my-app\\n📁 ├── src\\n📄 └── README.md"
  treer themes
        """,
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # ── create ──
    p_create = sub.add_parser("create", help="Create files/folders from a tree")
    p_create.add_argument("tree", nargs="*", help="Tree string (inline)")
    p_create.add_argument("--file", "-f", help=".tree or .txt file with the tree")
    p_create.add_argument("--output", "-o", default=".", help="Base directory (default: .)")
    p_create.set_defaults(func=cmd_create)

    # ── scan ──
    p_scan = sub.add_parser("scan", help="Scan a directory and print its tree")
    p_scan.add_argument("path", nargs="?", default=".", help="Directory to scan (default: .)")
    p_scan.add_argument("--style", "-s", default="plain",
                        choices=list(THEMES), help="Icon theme")
    p_scan.add_argument("--depth", "-d", type=int, default=None,
                        help="Max depth (default: unlimited)")
    p_scan.add_argument("--save", help="Save output to file")
    p_scan.set_defaults(func=cmd_scan)

    # ── theme ──
    p_theme = sub.add_parser("theme", help="Apply/change icons on an existing tree")
    p_theme.add_argument("tree", nargs="*", help="Tree string (inline)")
    p_theme.add_argument("--file", "-f", help=".tree or .txt file")
    p_theme.add_argument("--style", "-s", default="emoji",
                         choices=list(THEMES), help="Target icon theme")
    p_theme.add_argument("--save", help="Save output to file")
    p_theme.set_defaults(func=cmd_theme)

    # ── themes ──
    p_themes = sub.add_parser("themes", help="List all available themes")
    p_themes.set_defaults(func=cmd_themes)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
