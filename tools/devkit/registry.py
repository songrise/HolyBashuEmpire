"""Explicit check selection; full validation/build is always opt-in."""
from __future__ import annotations

import importlib
import os
import sys
import time
import unittest

from .common import read_json, utc_now, write_json

SCOPES = {
    "hygiene": ["validate_text_hygiene", "validate_variable_hygiene"],
    "local-affairs": ["validate_local_affairs"],
}
TESTS = {
    "devkit": ["test_devkit*.py"],
    "parser": ["test_eu5save.py"],
    "package": ["test_package_mod.py"],
    "hygiene": ["test_concept_labels.py", "test_text_hygiene.py", "test_variable_hygiene.py"],
    "build-support": ["test_build_support.py"],
}


def check(context, scope, output=None):
    rows = []
    manifest = read_json(context.mod / "build_manifest.json")
    if scope not in SCOPES:
        raise ValueError(f"Unknown check scope: {scope}")
    def record(name, passed):
        rows.append(dict(name=name, passed=bool(passed)))
    for name in SCOPES[scope]:
        module = importlib.import_module(name)
        module.validate(context.mod, context.root, context.path("game") / "game", manifest, record)
    result = dict(schema_version=1, kind="static", scope=scope, at=utc_now(),
                  status="passed" if all(r["passed"] for r in rows) else "failed", checks=rows)
    if output:
        write_json(output, result)
    return result


def unit(context, scope, output=None):
    if scope not in TESTS and scope != "all":
        raise ValueError(f"Unknown unit scope: {scope}")
    patterns = ["test_*.py"] if scope == "all" else TESTS[scope]
    previous, search_path = os.getcwd(), list(sys.path)
    started = time.perf_counter()
    try:
        os.chdir(context.root)
        sys.path.insert(0, str(context.root / 'tools'))
        suite = unittest.TestSuite()
        loader = unittest.TestLoader()
        for pattern in patterns:
            suite.addTests(loader.discover(str(context.root / 'tools'), pattern=pattern))
        result = unittest.TextTestRunner(verbosity=1).run(suite)
    finally:
        os.chdir(previous)
        sys.path[:] = search_path
    if output:
        write_json(output, dict(schema_version=1, kind='unit', scope=scope,
            at=utc_now(), status='passed' if result.wasSuccessful() else 'failed',
            tests=result.testsRun, passed=result.testsRun - len(result.failures) - len(result.errors) - len(result.skipped) - len(result.expectedFailures) - len(result.unexpectedSuccesses),
            skipped=[dict(test=str(case), reason=reason) for case, reason in result.skipped],
            failures=[dict(test=str(case), traceback=error) for case, error in result.failures],
            errors=[dict(test=str(case), traceback=error) for case, error in result.errors],
            expected_failures=len(result.expectedFailures), unexpected_successes=len(result.unexpectedSuccesses),
            elapsed_seconds=round(time.perf_counter() - started, 4)))
    return 0 if result.wasSuccessful() else 1
