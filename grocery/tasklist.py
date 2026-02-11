"""Google Tasks integration for grocery list management."""

import json
import subprocess
from thefuzz import fuzz
from .config import TASK_LIST_ID, PARENT_TASK_ID, get_aisle_index

LIST = TASK_LIST_ID
PARENT = PARENT_TASK_ID


def _run_gog(*args, parse_json=True) -> dict | str:
    """Run a gog tasks command and return parsed output."""
    cmd = ["gog", "tasks"] + list(args)
    if parse_json and "--json" not in args:
        cmd.append("--json")
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        stderr = result.stderr.strip()
        raise RuntimeError(f"gog tasks failed: {stderr or result.stdout.strip()}")
    if parse_json:
        return json.loads(result.stdout)
    return result.stdout


def get_items(include_completed=False) -> list[dict]:
    """Fetch grocery list items (sub-tasks of PARENT only)."""
    args = ["list", LIST]
    if include_completed:
        args += ["--show-completed", "--show-hidden"]
    data = _run_gog(*args)
    tasks = data.get("tasks", [])
    return [t for t in tasks if t.get("parent") == PARENT]


def add_item(title: str, previous_id: str = None) -> dict:
    """Add an item under the grocery list parent. Returns task dict."""
    args = ["add", LIST, "--title", title, "--parent", PARENT]
    if previous_id:
        args += ["--previous", previous_id]
    data = _run_gog(*args)
    return data.get("task", data)


def add_items_sorted(titles: list[str]) -> list[dict]:
    """Add multiple items, inserting each in the correct aisle-order position."""
    current = get_items(include_completed=False)
    
    current_indexed = [(t.get("title", ""), get_aisle_index(t.get("title", "")), t["id"]) for t in current if t.get("title")]
    current_indexed.sort(key=lambda x: (x[1], x[0].lower()))
    
    added = []
    for title in titles:
        new_aisle = get_aisle_index(title)
        new_key = (new_aisle, title.lower())
        
        previous_id = None
        for existing_title, existing_aisle, existing_id in current_indexed:
            existing_key = (existing_aisle, existing_title.lower())
            if existing_key <= new_key:
                previous_id = existing_id
            else:
                break
        
        task = add_item(title, previous_id=previous_id)
        task_id = task.get("id")
        added.append(task)
        
        insert_pos = 0
        for i, (_, a, _) in enumerate(current_indexed):
            if (a, current_indexed[i][0].lower()) <= new_key:
                insert_pos = i + 1
            else:
                break
        current_indexed.insert(insert_pos, (title, new_aisle, task_id))
    
    return added


def _fuzzy_find(name: str, items: list[dict]) -> dict | None:
    """Find best fuzzy match for name in items list."""
    best = None
    best_score = 0
    for item in items:
        score = fuzz.token_set_ratio(name.lower(), item["title"].lower())
        if score > best_score:
            best_score = score
            best = item
    if best_score >= 60:
        return best
    return None


def remove_item(title: str) -> str:
    """Remove item by fuzzy-matched title. Returns removed title."""
    items = get_items(include_completed=False)
    match = _fuzzy_find(title, items)
    if not match:
        raise ValueError(f"No matching item found for '{title}'")
    _run_gog("delete", LIST, match["id"], "--force", parse_json=False)
    return match["title"]


def check_item(title: str) -> str:
    """Mark item as completed. Returns matched title."""
    items = get_items(include_completed=False)
    match = _fuzzy_find(title, items)
    if not match:
        raise ValueError(f"No matching item found for '{title}'")
    _run_gog("done", LIST, match["id"])
    return match["title"]


def uncheck_item(title: str) -> str:
    """Mark completed item as active again. Returns matched title."""
    items = get_items(include_completed=True)
    completed = [t for t in items if t.get("status") == "completed"]
    match = _fuzzy_find(title, completed)
    if not match:
        raise ValueError(f"No matching completed item found for '{title}'")
    _run_gog("undo", LIST, match["id"])
    return match["title"]


def clear_completed() -> int:
    """Delete all completed sub-tasks of parent. Returns count deleted."""
    items = get_items(include_completed=True)
    completed = [t for t in items if t.get("status") == "completed"]
    count = 0
    for item in completed:
        try:
            _run_gog("delete", LIST, item["id"], "--force", parse_json=False)
            count += 1
        except RuntimeError:
            pass
    return count
