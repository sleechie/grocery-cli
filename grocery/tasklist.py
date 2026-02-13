"""Google Tasks integration for grocery list management."""

import json
import subprocess
from thefuzz import fuzz
from .config import TASK_LIST_ID, PARENT_TASK_ID, get_aisle_index

LIST = TASK_LIST_ID
PARENT = PARENT_TASK_ID


def parse_notes(notes: str) -> dict:
    """Extract structured fields from task notes. Returns dict with 'upc' and 'qty'."""
    result = {"upc": None, "qty": 1}
    if not notes:
        return result
    for line in notes.strip().split("\n"):
        line = line.strip()
        if line.startswith("UPC:"):
            result["upc"] = line[4:].strip()
        elif line.startswith("QTY:"):
            try:
                result["qty"] = int(line[4:].strip())
            except ValueError:
                pass
    return result


def build_notes(upc: str = None, qty: int = None) -> str:
    """Build notes string from UPC and quantity. Omits QTY if 1 or None."""
    parts = []
    if upc:
        parts.append(f"UPC:{upc}")
    if qty and qty > 1:
        parts.append(f"QTY:{qty}")
    return "\n".join(parts) if parts else ""


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


def add_item(title: str, previous_id: str = None, notes: str = None) -> dict:
    """Add an item under the grocery list parent. Returns task dict.
    
    Args:
        title: Item display name
        previous_id: ID of the sibling task to insert after (for ordering)
        notes: Optional notes/description (used to store UPC metadata)
    """
    args = ["add", LIST, "--title", title, "--parent", PARENT]
    if previous_id:
        args += ["--previous", previous_id]
    if notes:
        args += ["--notes", notes]
    data = _run_gog(*args)
    return data.get("task", data)


def add_items_sorted(titles: list[str], notes_map: dict = None) -> list[dict]:
    """Add multiple items, inserting each in the correct aisle-order position.
    
    Args:
        titles: List of item titles to add
        notes_map: Optional dict mapping title -> notes string (e.g. UPC metadata)
    """
    if notes_map is None:
        notes_map = {}
    
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
        
        notes = notes_map.get(title)
        task = add_item(title, previous_id=previous_id, notes=notes)
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
        if not item.get("title"):
            continue
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
