"""Explicit release plans. Planning and verification never publish content."""
from __future__ import annotations

import hashlib
import os
from contextlib import contextmanager
from pathlib import Path
import re
from uuid import uuid4

from .artifacts import inspect, unchanged
from .common import read_json, utc_now, write_json


def validate_description(text):
    if not text.strip() or len(text.encode("utf-8")) >= 8000:
        raise ValueError("Workshop description must be nonempty and below 8000 UTF-8 bytes")
    if "\x00" in text or re.search(r"\{\{.*?\}\}|TODO|PLACEHOLDER", text):
        raise ValueError("Description contains placeholders or NUL")
    stack = []
    paired = {"b", "i", "u", "h1", "h2", "h3", "list", "olist", "url", "img", "quote", "code", "spoiler", "strike", "table", "tr", "td", "th"}
    for match in re.finditer(r"\[(/?)([A-Za-z0-9]+)(?:=[^\]]*)?\]", text):
        closing, tag = match[1], match[2].lower()
        if tag not in paired:
            continue
        if closing:
            if not stack or stack.pop() != tag:
                raise ValueError("Unbalanced Workshop BBCode: " + tag)
        else:
            stack.append(tag)
    if stack:
        raise ValueError("Unclosed Workshop BBCode: " + ", ".join(stack))
    return text


def plan(context, *, artifact=None, descriptions=None, note="", output):
    descriptions = descriptions or {}
    if not artifact and not descriptions:
        raise ValueError("Select content and/or description files explicitly")
    if not note.strip() or "\x00" in note:
        raise ValueError("Provide a nonempty update note without NUL")
    configured = context.config["workshop"]
    if not set(descriptions) <= set(configured["languages"]):
        raise ValueError("Unknown Workshop language")
    texts = {}
    for language, path in descriptions.items():
        path = Path(path).resolve()
        text = validate_description(path.read_text(encoding="utf-8-sig"))
        texts[language] = dict(source=str(path), text=text,
                               sha256=hashlib.sha256(text.encode("utf-8")).hexdigest())
    value = dict(schema_version=1, plan_id=uuid4().hex, created=utc_now(), state="prepared",
        app_id=int(configured["app_id"]), item_id=int(configured["item_id"]),
        languages=configured["languages"], content=inspect(artifact, distribution=True) if artifact else None,
        descriptions=texts, note=note,
        scope=dict(content=bool(artifact), descriptions=list(texts), gallery=False, title=False, visibility=False))
    output = Path(output)
    if output.exists():
        raise FileExistsError("Preserve existing release plan: " + str(output))
    write_json(output, value)
    return value


def validate_plan(value):
    if value.get("schema_version") != 1 or not value.get("plan_id"):
        raise ValueError("Unsupported release plan")
    if not value.get("content") and not value.get("descriptions"):
        raise ValueError("Empty release plan")
    if len(value["languages"]) != len(set(value["languages"])) or not value["languages"]:
        raise ValueError("Invalid language inventory")
    if not set(value["descriptions"]) <= set(value["languages"]):
        raise ValueError("Unknown description language")
    for row in value["descriptions"].values():
        validate_description(row["text"])
        if hashlib.sha256(row["text"].encode("utf-8")).hexdigest() != row["sha256"]:
            raise ValueError("Description snapshot changed")
    if value.get("content"):
        unchanged(value["content"])
    return value


def compare(value, before, after):
    errors = []
    for lang in value["languages"]:
        a, b = before[lang], after[lang]
        for key in ("title", "visibility", "preview_url", "additional_previews"):
            if a.get(key) != b.get(key):
                errors.append(f"{lang}: unrelated {key} changed")
        expected = value["descriptions"].get(lang, {}).get("text", a["description"])
        if b["description"] != expected:
            errors.append(lang + ": description mismatch")
        if value.get("content") and value["plan_id"] not in b.get("metadata", ""):
            errors.append(lang + ": content plan marker missing")
    return errors


@contextmanager
def claim(plan_path):
    lock = Path(str(plan_path) + '.publish.lock')
    fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    os.close(fd)
    try:
        yield
    finally:
        lock.unlink(missing_ok=True)


def verify(plan_path, client):
    with claim(plan_path):
        return _verify(plan_path, client)


def _verify(plan_path, client):
    value = read_json(plan_path)
    if (client.app_id, client.item_id) != (value['app_id'], value['item_id']):
        raise ValueError('SDK target does not match plan')
    if not value.get("before"):
        raise ValueError("No submitted release evidence; verification cannot infer a previous upload")
    after = {lang: client.query(lang) for lang in value["languages"]}
    errors = compare(value, value["before"], after)
    value.update(state="verification_failed" if errors else "published_and_verified", after=after,
                 errors=errors, verified=utc_now())
    write_json(plan_path, value)
    return value


def publish(plan_path, client):
    with claim(plan_path):
        return _publish(plan_path, client)


def _publish(plan_path, client):
    value = validate_plan(read_json(plan_path))
    if value["state"] != "prepared":
        raise ValueError("Plan has already been attempted. Verify its outcome before preparing another plan")
    if (client.app_id, client.item_id) != (value["app_id"], value["item_id"]):
        raise ValueError("SDK target does not match plan")
    value["before"] = {lang: client.query(lang) for lang in value["languages"]}
    value["state"] = "submitting"
    value["operations_completed"] = []
    # Record intent before any network mutation; timeout never triggers an automatic retry.
    write_json(plan_path, value)
    try:
        if value.get("content"):
            import json
            previous = value["before"][value["languages"][0]].get("metadata", "")
            metadata = json.loads(previous) if previous else {}
            if not isinstance(metadata, dict):
                raise ValueError("Existing Workshop metadata must be an object")
            metadata.update(devkit_plan=value["plan_id"], version=value["content"]["version"],
                            manifest_sha256=value["content"]["manifest_sha256"])
            client.submit(content=value["content"]["path"], metadata=json.dumps(metadata, ensure_ascii=False), note=value["note"])
            value["operations_completed"].append("content")
            write_json(plan_path, value)
        for lang, description in value["descriptions"].items():
            client.submit(language=lang, description=description["text"], note=value["note"])
            value["operations_completed"].append("description:" + lang)
            write_json(plan_path, value)
        value["state"] = "submitted"
        write_json(plan_path, value)
    except BaseException as exc:
        value.update(state="outcome_unknown", error=str(exc))
        write_json(plan_path, value)
        raise
    return _verify(plan_path, client)
