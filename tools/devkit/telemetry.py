"""Opt-in passive counters in isolated profiles, never production artifacts."""
from __future__ import annotations

import hashlib
import re

from pdxscript import blocks, apply_edits


def instrument_affairs(mod, catalogue):
    path = mod / "in_game/common/scripted_effects/hbe_af_effects.txt"
    original = path.read_bytes()
    text = original.decode("utf-8-sig")
    if "hbe_probe_initialized" in text:
        raise ValueError("Profile is already instrumented")
    projects = {str(p["id"]): p for p in catalogue["projects"]}
    edits, seen = [], set()
    def count(name, value="1"):
        return f" change_variable = {{ name = hbe_probe_{name} add = {value} }} "
    for key, _, a, b, _ in blocks(text, 0):
        body = text[a:b]
        match = re.fullmatch(r"hbe_af_(start|reward)_(\d+)_(small|large)", key)
        if match:
            action, pid, tier = match.groups()
            project = projects[pid]
            label = "starts" if action == "start" else "completed"
            extra = count(label) + count(label + "_" + project["pool"]) + count(label + "_" + tier) + count(f"{label}_p{pid}_{tier}")
            if action == "start":
                extra += count("gold_paid", "var:hbe_af_paid") + count("burden_paid", "var:hbe_af_load")
                inner = next(row for row in blocks(body, 0) if row[0] == "if")
                edits.append((a + inner[3], a + inner[3], extra))
            else:
                extra += " if = { limit = { var:hbe_af_outcome = 4 } " + count("great_completed") + " } "
                for i, reward in enumerate(project["rewards"]):
                    extra += count("reward_" + reward["type"], f"var:hbe_af_actual_{i}")
                edits.append((b, b, extra))
            seen.add(key)
        elif key == "hbe_af_cancel":
            inner = next(row for row in blocks(body, 0) if row[0] == "if")
            edits.append((a + inner[3], a + inner[3], count("cancelled")))
        elif key == "hbe_af_monthly":
            extra = count("months")
            for name, condition in (
                ("active_months", "has_variable = hbe_af_active"),
                ("paused_months", "has_variable = hbe_af_active has_variable = hbe_af_pause var:hbe_af_pause > 0"),
                ("war_months", "at_war = yes"),
                ("affordable_idle_months", "hbe_af_idle = yes NOT = { at_war = yes } hbe_af_available = yes"),
                ("high_burden_months", "var:hbe_burden > 50")):
                extra += " if = { limit = { " + condition + " } " + count(name) + " } "
            edits.append((b, b, extra))
        elif key == "hbe_af_ai_consider":
            for persona in catalogue["ai_participation"]["personalities"]:
                ident, chance, label = persona["id"], persona["chance"], persona["key"]
                pattern = (rf"(var:hbe_af_ai_personality\s*=\s*{ident}\s*\}})\s*"
                           rf"(random\s*=\s*\{{\s*chance\s*=\s*{chance}\s+)(hbe_af_auto_start\s*=\s*yes)")
                body, n = re.subn(pattern, lambda m: m[1] + count("eligible_" + label) + m[2] + count("accepted_" + label) + m[3], body)
                if n != 1:
                    raise ValueError("AI telemetry anchor changed: " + label)
            edits.append((a, b, body))
        elif key == "hbe_af_auto_choose":
            edits.append((b, b, count("auto_evaluations") + " if = { limit = { var:hbe_af_choice <= 0 } " + count("no_candidate") + " } else_if = { limit = { var:hbe_af_best < 7 } " + count("below_score") + " } "))
    expected = {f"hbe_af_{action}_{pid}_{tier}" for pid in projects for action in ("start", "reward") for tier in ("small", "large")}
    if seen != expected:
        raise ValueError("Project telemetry coverage mismatch")
    result = apply_edits(text, edits)
    names = sorted(set(re.findall(r"name = (hbe_probe_\w+)", result)))
    init = " ".join("set_variable = { name = " + name + " value = 0 }" for name in names)
    result, n = re.subn(r"hbe_af_initialize\s*=\s*\{", lambda m: m[0] + " if = { limit = { NOT = { has_variable = hbe_probe_initialized } } set_variable = hbe_probe_initialized " + init + " }", result)
    if n != 1:
        raise ValueError("Initialization telemetry anchor changed")
    list(blocks(result, 0))
    # No random statements are added; failed anchors abort before writing anything.
    if len(re.findall(r"\brandom\s*=", result)) != len(re.findall(r"\brandom\s*=", text)):
        raise ValueError("Telemetry changed RNG structure")
    path.write_text(result, encoding="utf-8-sig", newline="\n")
    return dict(adapter="local-affairs:1", counters=names,
                source_sha256=hashlib.sha256(original).hexdigest(),
                instrumented_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                note="Counters only; no grants, RNG draws or production artifact edits. Peak burden is read from checkpoints.")
