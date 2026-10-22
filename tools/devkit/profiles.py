"""Isolated EU5 scenarios. Configuration changes replace copied launcher scripts."""
from __future__ import annotations

import re
import calendar
import shutil
from pathlib import Path
from uuid import uuid4

from .artifacts import inspect, unchanged
from .common import read_json, utc_now, within, write_json


def date_key(value):
    if not isinstance(value, str):
        raise ValueError("Missing game date")
    parts = tuple(map(int, value.split(".")))
    if (len(parts) != 3 or parts[0] < 1 or not 1 <= parts[1] <= 12 or
            not 1 <= parts[2] <= calendar.monthrange(parts[0], parts[1])[1]):
        raise ValueError("Invalid game date: " + value)
    return parts


def observation(years, interval=5, start="1337.4.2"):
    year, month, day = date_key(start)
    if years <= 0 or interval <= 0:
        raise ValueError("Years and checkpoint interval must be positive")
    if day > 28:
        raise ValueError("Recurring checkpoints require a start day from 1–28")
    offsets = sorted({0, years, *range(interval, years, interval)})
    return dict(schema_version=1, name="natural-observer", mode="natural",
                months=years * 12 + 1,
                checkpoints=[f"{year + n}.{month}.{day}" for n in offsets],
                test_name="hbe_dev_observe", telemetry="local-affairs", fixtures=[])


def validate(scenario):
    if scenario.get("schema_version") != 1 or scenario.get("mode") not in ("natural", "controlled"):
        raise ValueError("Unsupported scenario schema or mode")
    if not re.fullmatch(r"[A-Za-z_][A-Za-z_0-9]*", scenario.get("test_name", "")):
        raise ValueError("Invalid engine test name")
    if type(scenario.get("months")) is not int or not 1 <= scenario["months"] <= 12000:
        raise ValueError("Scenario months must be an integer in 1–12000")
    dates = [date_key(value) for value in scenario.get("checkpoints", [])]
    if not dates or dates != sorted(set(dates)):
        raise ValueError("Checkpoints must be nonempty, unique and increasing")
    if scenario["mode"] == "natural" and scenario.get("fixtures"):
        raise ValueError("Natural observation cannot inject controlled fixtures")
    if scenario.get("telemetry") not in (None, "local-affairs"):
        raise ValueError("Unknown telemetry adapter")
    if not isinstance(scenario.get('name'), str) or not scenario['name'].strip():
        raise ValueError('Provide a scenario name')
    for rule in scenario.get('assertions', []):
        if not all(isinstance(rule.get(k), str) and rule[k] for k in ('name', 'country', 'variable')):
            raise ValueError('Invalid assertion identity')
        if ('equals' in rule) == bool(rule.get('absent')):
            raise ValueError('Each assertion must specify equals or absent')
    return scenario


def prepare(context, scenario, *, run_id=None, settings=None, artifact=None):
    validate(scenario)
    run_id = run_id or (utc_now().replace(":", "").replace("+", "_") + "-" + uuid4().hex[:8])
    if not re.fullmatch(r"[A-Za-z0-9_.-]+", run_id):
        raise ValueError("Run ID must be a simple directory name")
    run = within(context.path("runs"), context.path("runs") / run_id)
    if run.exists():
        raise FileExistsError("Preserve previous run: " + str(run))
    source = Path(artifact).resolve() if artifact else context.mod
    if source == run or source in run.parents or run in source.parents:
        raise ValueError('Artifact and run directories must be independent')
    identity = inspect(source)
    template = Path(settings).resolve() if settings else context.path("settings_template")
    # Only copy settings, never account data, player saves or a previous test mod.
    settings_doc = read_json(template)
    if not isinstance(settings_doc, dict):
        raise ValueError("Settings template must be a JSON object")
    fixtures = []
    for item in scenario.get("fixtures", []):
        src = within(context.root, context.root / item["source"])
        within(run / "mod/holy_bashu_empire", run / "mod/holy_bashu_empire" / item["target"])
        if not src.is_file():
            raise FileNotFoundError(src)
        fixtures.append((src, item["target"]))
    run.mkdir(parents=True)
    write_json(run / "status.json", dict(state="preparing", updated=utc_now()))
    try:
        mod = run / "mod/holy_bashu_empire"
        shutil.copytree(source, mod)
        unchanged(identity)
        for src, target in fixtures:
            dest = within(mod, mod / target)
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dest)
        write_json(run / "pdx_settings.json", settings_doc)
        write_json(run / "playsets.json", dict(file_version="1.0.0", playsets=[dict(
            name=f"HBE {identity['version']} {scenario['name']}", isActive=True,
            isAutomaticallySorted=True, orderedListMods=[dict(path=mod.as_posix() + "/", isEnabled=True)],
            DLC=[dict(paradoxAppId="d000_shared", isEnabled=True)])]))
        if scenario["mode"] == "natural":
            last = scenario["checkpoints"][-1]
            test = mod / "in_game/common/tests" / (scenario["test_name"] + ".txt")
            test.parent.mkdir(parents=True, exist_ok=True)
            test.write_text(f"{scenario['test_name']} = {{ year = {date_key(scenario['checkpoints'][0])[0]} "
                f"end_year = {date_key(last)[0] + 1} fail_on_end_year = yes "
                f"success = {{ current_date >= {last} }} success_effect = {{ test_log = HBE_DEV_OBSERVE_REACHED }} }}\n",
                encoding="utf-8-sig")
        telemetry = None
        catalogue_path = context.root / 'data/local_affairs_projects.json'
        if catalogue_path.is_file():
            shutil.copy2(catalogue_path, run / 'catalogue.json')
        if scenario.get("telemetry") == "local-affairs":
            from .telemetry import instrument_affairs
            telemetry = instrument_affairs(mod, read_json(run / 'catalogue.json'))
        provenance = dict(schema_version=1, run_id=run_id, created=utc_now(), artifact=identity,
                          scenario=scenario, telemetry=telemetry,
                          executable=str(context.executable), root=str(context.root))
        write_json(run / "provenance.json", provenance)
        write_json(run / "status.json", dict(state="prepared", updated=utc_now()))
    except BaseException as exc:
        write_json(run / "status.json", dict(state="prepare_failed", error=str(exc), updated=utc_now()))
        raise
    return run
