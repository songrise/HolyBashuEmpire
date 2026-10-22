"""A thin command facade; individual modules are reusable from Python."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
import sys

from .common import read_json, write_json
from .context import Context


def parser():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root", type=Path)
    ap.add_argument("--config", type=Path, help="Machine-local configuration override")
    commands = ap.add_subparsers(dest="command", required=True)
    commands.add_parser("doctor")
    from .registry import SCOPES, TESTS
    p = commands.add_parser("check"); p.add_argument("--scope", choices=SCOPES, default="hygiene"); p.add_argument("--output", type=Path)
    p = commands.add_parser("unit"); p.add_argument("--scope", choices=[*TESTS, "all"], default="devkit"); p.add_argument("--output", type=Path)
    p = commands.add_parser("test"); p.add_argument("--scenario", type=Path, default=Path("tools/scenarios/affairs-balance.json"))
    p.add_argument("--settings", type=Path); p.add_argument("--artifact", type=Path); p.add_argument("--run-id"); p.add_argument("--execute", action="store_true"); p.add_argument("--timeout", type=int, default=7200)
    p = commands.add_parser("observe"); p.add_argument("--years", type=int, required=True); p.add_argument("--checkpoint-years", type=int, default=5); p.add_argument("--start", default="1337.4.2")
    p.add_argument("--settings", type=Path); p.add_argument("--artifact", type=Path); p.add_argument("--run-id"); p.add_argument("--execute", action="store_true"); p.add_argument("--timeout", type=int, default=7200)
    for name in ("run", "stop", "status", "report", "archive"):
        p = commands.add_parser(name); p.add_argument("--run", type=Path, required=True)
        if name == "run": p.add_argument("--timeout", type=int, default=7200)
        if name == "report":
            p.add_argument("--output", type=Path); p.add_argument("--baseline", type=Path); p.add_argument("--cache", type=Path)
            p.add_argument("--assertions-from", type=Path); p.add_argument("--receipt", type=Path)
        if name == "archive": p.add_argument("--output", type=Path, required=True); p.add_argument("--include-saves", action="store_true")
    p = commands.add_parser("logs"); p.add_argument("folder", type=Path); p.add_argument("--baseline", type=Path); p.add_argument("--output", type=Path)
    p = commands.add_parser("artifact"); p.add_argument("path", type=Path); p.add_argument("--hashes", action="store_true")
    p = commands.add_parser("media"); p.add_argument("--template", type=Path, required=True); p.add_argument("--output", type=Path, required=True)
    p = commands.add_parser("package"); p.add_argument("--source", type=Path); p.add_argument("--output", type=Path, required=True); p.add_argument("--report", type=Path, required=True); p.add_argument("--texconv", type=Path); p.add_argument("--workers", type=int, default=2)
    p = commands.add_parser("release-plan"); p.add_argument("--artifact", type=Path); p.add_argument("--description", action="append", default=[], metavar="LANG=FILE"); p.add_argument("--note-file", type=Path, required=True); p.add_argument("--output", type=Path, required=True)
    for name in ("publish", "verify-release"):
        p = commands.add_parser(name); p.add_argument("--plan", type=Path, required=True)
    p = commands.add_parser("stages")
    p = commands.add_parser("build"); p.add_argument("--output", type=Path)
    p = commands.add_parser("install"); p.add_argument("--userdir", type=Path, required=True); p.add_argument("--mod-directory", type=Path); p.add_argument("--update-playset", action="store_true")
    return ap


def main(argv=None):
    ap = parser()
    args = ap.parse_args(argv)
    try:
        context = Context.load(args.root, args.config)
        result = dispatch(context, args)
        if isinstance(result, int):
            return result
        # Keep large snapshot/inventory data in report files, not terminal output.
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 1 if result.get("status") == "failed" or result.get("analysis_status") == "failed" or result.get("validation_status") == "failed" or result.get("errors") else 0
    except (OSError, ValueError, RuntimeError, KeyError, subprocess.SubprocessError) as exc:
        print(f"{type(exc).__name__}: {exc}", file=sys.stderr)
        return 2


def dispatch(context, args):
    cmd = args.command
    if cmd == "doctor": return context.doctor()
    if cmd in ("check", "unit"):
        from .registry import check, unit
        if cmd == 'unit': return unit(context, args.scope, args.output)
        result = check(context, args.scope, args.output)
        return dict(status=result['status'], scope=args.scope, check_count=len(result['checks']),
                    failed=[r['name'] for r in result['checks'] if not r['passed']], report=str(args.output) if args.output else None)
    if cmd in ("test", "observe"):
        from .profiles import observation, prepare
        scenario = observation(args.years, args.checkpoint_years, args.start) if cmd == "observe" else read_json(context.root / args.scenario)
        run = prepare(context, scenario, run_id=args.run_id, settings=args.settings, artifact=args.artifact)
        if args.execute:
            from .runner import run_profile
            result = run_profile(run, timeout=args.timeout)
            return dict(run=str(run), state=result["run_state"], analysis_status=result["analysis_status"], validation_status=result['validation_status'])
        return dict(state="prepared", run=str(run), launch="python tools/dev.py run --run \"" + str(run) + "\"")
    if cmd == "run":
        from .runner import run_profile
        r = run_profile(args.run, timeout=args.timeout)
        return dict(state=r["run_state"], analysis_status=r["analysis_status"], validation_status=r['validation_status'])
    if cmd == "stop":
        from .runner import request_stop
        return request_stop(args.run)
    if cmd == "status": return read_json(args.run / "status.json")
    if cmd == "report":
        from .reporting import analyze_run, receipt
        r = analyze_run(args.run, output=args.output, baseline=args.baseline, cache_dir=args.cache, assertions_from=args.assertions_from)
        if args.receipt: write_json(args.receipt, receipt(r))
        return dict(state=r["run_state"], analysis_status=r["analysis_status"], validation_status=r['validation_status'],
                    last_date=r['observation']['last_date'], checkpoints=len(r['snapshots']),
                    missing_checkpoints=r['observation']['missing_checkpoints'],
                    assertions=r['engine']['controlled_assertions']['status'], diagnostics=r["diagnostics"]["counts"])
    if cmd == "logs":
        from .diagnostics import audit
        result = audit(args.folder, read_json(args.baseline) if args.baseline else None)
        if args.output: write_json(args.output, result)
        return dict(counts=result["counts"], groups=len(result["groups"]), logs_present=result["logs_present"])
    if cmd == "artifact":
        from .artifacts import inspect
        return {k: v for k, v in inspect(args.path, hashes=args.hashes).items() if k != "files"}
    if cmd == "media":
        from .media import compose
        return compose(args.template, args.output)
    if cmd == "package":
        from package_mod import build
        report = build(args.source or context.mod, args.output, texconv=args.texconv, workers=args.workers)
        write_json(args.report, report)
        return {k: v for k, v in report.items() if k != "files"}
    if cmd == "release-plan":
        from .workshop import plan
        descriptions = {}
        for item in args.description:
            lang, path = item.split("=", 1)
            if lang in descriptions: raise ValueError("Duplicate language: " + lang)
            descriptions[lang] = path
        result = plan(context, artifact=args.artifact, descriptions=descriptions,
                      note=args.note_file.read_text(encoding="utf-8-sig"), output=args.output)
        return dict(plan=str(args.output), plan_id=result["plan_id"], scope=result["scope"])
    if cmd in ("publish", "verify-release"):
        from .steam import Steam
        from .workshop import publish, verify, validate_plan
        plan = read_json(args.plan)
        if cmd == "publish": validate_plan(plan)
        configured = context.config["workshop"]
        if (plan["app_id"], plan["item_id"]) != (configured["app_id"], configured["item_id"]):
            raise ValueError("Release target differs from project configuration")
        with Steam(context.path("game") / "binaries/steam_api64.dll", plan["app_id"], plan["item_id"]) as client:
            result = (publish if cmd == "publish" else verify)(args.plan, client)
        return dict(state=result["state"], errors=result["errors"])
    if cmd == "stages":
        from .pipeline import FINAL_STAGES
        return dict(final_stages=[s.__dict__ for s in FINAL_STAGES], parallel=False, partial_build=False)
    if cmd == "build":
        command = [sys.executable, "-B", str(context.root / "tools/build_mod.py"), "--game-dir", str(context.path("game"))]
        if args.output: command += ["--output", str(args.output)]
        return subprocess.run(command, cwd=context.root, check=False).returncode
    if cmd == "install":
        command = ["powershell", "-NoProfile", "-File", str(context.root / "Install-Mod.ps1"), "-UserDataPath", str(args.userdir), "-GamePath", str(context.path("game"))]
        if args.mod_directory: command += ["-ModDirectory", str(args.mod_directory)]
        if args.update_playset: command += ["-UpdatePlayset"]
        return subprocess.run(command, cwd=context.root, check=False).returncode
    if cmd == "archive":
        from .archive import archive
        return archive(args.run, args.output, saves=args.include_saves)
    raise ValueError(cmd)
