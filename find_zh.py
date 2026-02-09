#!/usr/bin/env python3
"""Find remaining hardcoded Chinese strings in Python files."""
import os
import re

root = r"D:\Newidea-3\sanguosha_backup_20260121_071454"
zh_pat = re.compile(r"[\u4e00-\u9fff]")
skip_dirs = {".git", "__pycache__", "node_modules", ".pytest_cache", "venv", "docs"}

for dirpath, dirnames, filenames in os.walk(root):
    dirnames[:] = [d for d in dirnames if d not in skip_dirs]
    for fn in filenames:
        if not fn.endswith(".py"):
            continue
        fp = os.path.join(dirpath, fn)
        with open(fp, encoding="utf-8", errors="ignore") as f:
            in_docstring = False
            for i, line in enumerate(f, 1):
                stripped = line.strip()
                # Skip pure comments
                if stripped.startswith("#"):
                    continue
                # Track docstrings (simple heuristic)
                triple_count = stripped.count('"""') + stripped.count("'''")
                if triple_count == 1:
                    in_docstring = not in_docstring
                    continue
                if triple_count >= 2:
                    continue
                if in_docstring:
                    continue
                # Check for Chinese chars NOT in _t() calls
                if zh_pat.search(line) and "_t(" not in line:
                    code_part = line.split("#")[0]
                    if zh_pat.search(code_part):
                        rel = os.path.relpath(fp, root)
                        print(f"{rel}:{i}: {stripped[:120]}")
