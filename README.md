# Tree Flow

A simple CLI tool to **create**, **scan**, and **theme** directory trees.

---

## Install

```bash
# No dependencies — just Python 3.6+
python main.py --help
# Or make it executable:
chmod +x main.py && mv main.py /usr/local/bin/main
```

---

## Commands

### `create` — Build a folder tree from text

```bash
# Inline string
python main.py create "my-app
├── main.py
├── requirements.txt
└── config
    └── settings.py"

# From a .tree or .txt file
python main.py create --file examples/sample.tree

# Into a specific directory
python main.py create --file examples/sample.tree --output ./workspace
```

**Supported input formats:**
```
my-project              ← root (becomes a folder)
├── bot.py              ← file
├── points.json         ← file
└── src                 ← folder (no extension = folder)
    ├── app.py
    └── utils.py
```

---

### `scan` — Print a directory tree

```bash
# Plain tree of current dir
python main.py scan

# With emoji icons, 3 levels deep
python main.py scan . --style emoji --depth 3

# Nerd font icons, saved to file
python main.py scan /path/to/project --style nerd --save mytree.tree
```

---

### `theme` — Change icons on an existing tree

```bash
# Apply emoji to a plain tree file
python main.py theme --file mytree.tree --style emoji

# Convert emoji tree back to plain
python main.py theme --style plain --file mytree.tree

# Inline
python main.py theme --style retro "my-app
├── main.py
└── README.md"
```

---

### `themes` — List all themes

```bash
python main.py themes
```

#### Available themes

| Theme     | Description                                          | Example                  |
|-----------|------------------------------------------------------|--------------------------|
| `plain`   | No icons — clean tree lines                          | `├── main.py`            |
| `emoji`   | Emoji icons per file type                            | `├── 🐍 main.py`         |
| `nerd`    | Nerd Font icons (needs patched font)                 | `├──  main.py`          |
| `minimal` | ASCII `+` and `·` markers                            | `├── · main.py`          |
| `retro`   | DOS-style `[DIR]` / `[.py]` labels                  | `├── [.py] main.py`      |

---

## Tree file format (`.tree` / `.txt`)

Just paste any tree — from your terminal, IDE, or hand-written:

```
my-bot-project
├── bot.py
├── points.json
├── requirements.txt
├── config
│   ├── settings.py
│   └── .env
└── utils
    ├── helpers.py
    └── logger.py
```

Save as `project.tree` or `project.txt`, then run:

```bash
python main.py create --file project.tree
```

---

## Examples

```bash
# 1. Scan current dir with emoji, save it
python main.py scan . --style emoji --save my_project.tree

# 2. Transform that saved tree to nerd-font style
python main.py theme --file my_project.tree --style nerd

# 3. Create a fresh project from a tree file
python main.py create --file my_project.tree --output ./new_workspace

# 4. Quick inline creation
python main.py create "api-server
├── main.py
├── models.py
├── routes.py
└── tests
    └── test_main.py"
```
