"""Classify complete multiline diagnostics without discarding engine errors."""
from __future__ import annotations

from collections import Counter
from pathlib import Path
import re

HEAD = re.compile(r"(?m)(?=^\[[0-9:.]+\]\[)")
REGISTRATION = re.compile(r"Possible match:|is orphaned|was not used by the script or code|"
                          r"used but (?:is )?never set|set but (?:is )?never used|"
                          r"is (?:used|set).*?but (?:is )?never", re.I)


def normalize(message):
    value = re.sub(r"^\[[0-9:.]+\]", "[time]", message)
    value = re.sub(r"\b0x[0-9a-fA-F]+\b", "<address>", value)
    # Country IDs and values are meaningful: deliberately do not erase all numbers.
    return value.strip()


def classify(message):
    if REGISTRATION.search(message):
        return "registration"
    if re.search(r"pdx_data_(?:factory|localize)|gui.*\.cpp|loc string", message, re.I):
        return "gui_localization"
    if re.search(r"missing texture|could not (?:open|find) (?:file|texture)|failed.*(?:texture|asset)", message, re.I):
        return "resource"
    if re.search(r"jomini_(?:effect|trigger|script)|unknown (?:effect|trigger)|invalid scope", message, re.I):
        return "script"
    return "engine_other"


def audit(folder, baseline=None):
    folder = Path(folder)
    if not folder.is_dir():
        raise FileNotFoundError(folder)
    if baseline and 'diagnostics' in baseline:
        baseline = baseline['diagnostics']
    grouped = {}
    files = {}
    for path in sorted(folder.glob("error*.log")):
        text = path.read_text(encoding="utf-8-sig", errors="replace")
        files[path.name] = dict(bytes=path.stat().st_size, lines=len(text.splitlines()))
        for part in HEAD.split(text):
            if not part.strip():
                continue
            key = normalize(part)
            entry = grouped.setdefault(key, dict(message=key, category=classify(part),
                hbe_mentioned=bool(re.search(r"\bhbe[_0-9]", part, re.I)), count=0,
                files=[], first_header=part.splitlines()[0], last_header=None))
            entry["count"] += 1
            entry["last_header"] = part.splitlines()[0]
            if path.name not in entry["files"]:
                entry["files"].append(path.name)
    old = {r["message"]: r["count"] for r in (baseline or {}).get("groups", [])}
    for key, row in grouped.items():
        row["baseline_count"] = old.get(key) if baseline is not None else None
        row["new_since_baseline"] = key not in old if baseline is not None else None
    counts = Counter()
    for row in grouped.values():
        counts[row["category"]] += row["count"]
    return dict(schema_version=1, files=files, logs_present=bool(files),
                counts=dict(counts), groups=list(grouped.values()),
                scope="All error*.log diagnostics retained. HBE mention is a search hint, not attribution. "
                      "Baseline presence does not prove a message harmless.")
