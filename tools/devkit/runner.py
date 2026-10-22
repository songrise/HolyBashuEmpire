"""Supervised processes with explicit stop/failure states and atomic status."""
from __future__ import annotations

import os
from pathlib import Path
import subprocess
import time

from .common import read_json, utc_now, write_json
from .profiles import validate
from .processes import identity as process_identity, terminate_matching, command_arguments


def arguments(run, provenance):
    scenario = validate(provenance["scenario"])
    return [provenance["executable"], "-debug_mode", "-nographics", "-skip", "-observe", "-handsoff",
            f"-timed_handsoff={scenario['months']}",
            "-handsoff_save_at_dates=" + "|".join(scenario["checkpoints"]),
            "-force_text_save", "-automated_test", "-test=" + scenario["test_name"],
            "-userdir=" + Path(run).resolve().as_posix()]


def matches_process(current, expected, run):
    if (not current or not expected or not current.get("executable") or not current.get("command_line")
            or not expected.get("created") or not expected.get("executable")):
        return False
    normalize = lambda s: str(s).replace("\\", "/").replace('"', "").casefold()
    command = [normalize(arg) for arg in command_arguments(current["command_line"])]
    target = "-userdir=" + normalize(Path(run).resolve())
    userdir_matches = [arg for arg in command if arg.startswith("-userdir=")] == [target]
    return (current.get("pid") == expected.get("pid") and
            current.get("created") == expected.get("created") and
            normalize(current["executable"]) == normalize(expected["executable"]) and userdir_matches)


def request_stop(run, reason="user requested stop"):
    run = Path(run).resolve()
    status = read_json(run / "status.json")
    if status["state"] not in ("running", "stopping"):
        raise ValueError("Run is not running")
    expected = read_json(run / "process.json")
    current = process_identity(expected["pid"])
    if not matches_process(current, expected, run):
        raise RuntimeError("Process identity changed; refusing to stop an unrelated process")
    terminate_matching(expected, run, matches_process,
        lambda: write_json(run / "stop-request.json", dict(reason=reason, at=utc_now())))
    return dict(state="stop_requested", pid=expected["pid"], reason=reason)


def run_profile(run, *, timeout=7200, analyze=True, poll_seconds=2):
    run = Path(run).resolve()
    provenance = read_json(run / "provenance.json")
    if read_json(run / "status.json")["state"] != "prepared":
        raise ValueError("Only a prepared run may be launched once")
    if timeout <= 0:
        raise ValueError("Timeout must be positive")
    args = arguments(run, provenance)
    if not Path(args[0]).is_file():
        raise FileNotFoundError(args[0])
    # O_EXCL prevents competing supervisors from launching the same profile.
    lock = run / "supervisor.lock"
    fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    os.close(fd)
    proc = None
    phase = "process"
    write_json(run / "launch.json", dict(args=args, started=utc_now()))
    try:
        with (run / "stdout.txt").open("wb") as out, (run / "stderr.txt").open("wb") as err:
            proc = subprocess.Popen(args, cwd=Path(args[0]).parents[1], stdout=out, stderr=err,
                                    creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            identity = process_identity(proc.pid)
            if identity is None:
                # A quick launch failure can occur before CIM sees the process.
                identity = dict(pid=proc.pid, executable=args[0], created=None, command_line=None)
            write_json(run / "process.json", identity)
            write_json(run / "status.json", dict(state="running", pid=proc.pid, updated=utc_now()))
            started = time.monotonic()
            timed_out = False
            while proc.poll() is None:
                if time.monotonic() - started >= timeout:
                    timed_out = True
                    proc.terminate()
                    break
                time.sleep(poll_seconds)
            code = proc.wait(timeout=30)
        stopped = (run / "stop-request.json").exists()
        state = "stopped_by_user" if stopped else "timed_out" if timed_out else "exited" if code == 0 else "process_failed"
        write_json(run / "completion.json", dict(state=state, exit_code=code, finished=utc_now()))
        write_json(run / "status.json", dict(state=state, exit_code=code, updated=utc_now()))
        if analyze:
            phase = "analysis"
            from .reporting import analyze_run
            return analyze_run(run)
        return read_json(run / "completion.json")
    except BaseException as exc:
        if proc is not None and proc.poll() is None:
            proc.terminate()
            proc.wait(timeout=30)
        write_json(run / "status.json", dict(state="analysis_failed" if phase == "analysis" else "supervisor_failed", error=str(exc), updated=utc_now()))
        raise
    finally:
        lock.unlink(missing_ok=True)
