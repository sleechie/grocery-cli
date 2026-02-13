#!/usr/bin/env python3
"""Migration: move (Nx) from titles into QTY notes field."""

import json
import re
import subprocess

from dotenv import load_dotenv
load_dotenv()

import os
LIST = os.getenv("GROCERY_TASK_LIST_ID")

def run_gog(*args):
    cmd = ["gog", "tasks"] + list(args) + ["--json"]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"gog failed: {r.stderr.strip()}")
    return json.loads(r.stdout)

def parse_upc(notes):
    if not notes:
        return None
    for line in notes.strip().split("\n"):
        if line.strip().startswith("UPC:"):
            return line.strip()[4:].strip()
    return None

def build_notes(upc=None, qty=None):
    parts = []
    if upc:
        parts.append(f"UPC:{upc}")
    if qty and qty > 1:
        parts.append(f"QTY:{qty}")
    return "\n".join(parts)

def main():
    data = run_gog("list", LIST, "--show-completed", "--show-hidden")
    tasks = data.get("tasks", [])
    
    pattern = re.compile(r"\s*\((\d+)x\)\s*$")
    
    migrated = 0
    for task in tasks:
        title = task.get("title", "")
        m = pattern.search(title)
        if not m:
            continue
        
        qty = int(m.group(1))
        new_title = title[:m.start()].strip()
        
        existing_upc = parse_upc(task.get("notes", ""))
        new_notes = build_notes(upc=existing_upc, qty=qty)
        
        task_id = task["id"]
        print(f"  Migrating: '{title}' -> '{new_title}' [QTY:{qty}]")
        
        args = ["update", LIST, task_id, "--title", new_title]
        if new_notes:
            args += ["--notes", new_notes]
        run_gog(*args)
        migrated += 1
    
    print(f"\nMigrated {migrated} item(s).")

if __name__ == "__main__":
    main()
