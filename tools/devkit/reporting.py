"""One result model for partial observations, diagnostics and Markdown reports."""
from __future__ import annotations

from pathlib import Path
import re

from eu5save import load_snapshot, anomalies
from eu5save.errors import SaveError
from eu5save.hbe import project_summary

from .common import read_json, utc_now, write_json
from .diagnostics import audit
from .profiles import date_key


def summarize(snapshots, scenario):
    rows = sorted(snapshots, key=lambda row: date_key(row["date"]))
    playthroughs = {row.get("playthrough_id") for row in rows}
    if rows and (None in playthroughs or len(playthroughs) != 1):
        raise ValueError("Refusing to combine missing or mixed playthrough identities")
    dates = {row["date"] for row in rows}
    missing = [date for date in scenario["checkpoints"] if date not in dates]
    last = rows[-1] if rows else None
    last_countries = last["countries"] if last else []
    first_by_id = {(r["id"], r["tag"]): r for r in rows[0]["countries"]} if rows else {}
    changes = []
    for row in last_countries:
        old = first_by_id.get((row["id"], row["tag"]))
        changes.append(dict(id=row["id"], tag=row["tag"], alive=row["alive"],
            completed=row["affairs"]["completed"],
            completed_change=row["affairs"]["completed"] - old["affairs"]["completed"] if old else None,
            gold_change=row["gold"] - old["gold"] if old and row["gold"] is not None and old["gold"] is not None else None))
    return dict(target_reached=bool(last and date_key(last["date"]) >= date_key(scenario["checkpoints"][-1])),
                missing_checkpoints=missing, checkpoint_coverage_complete=not missing,
                last_date=last["date"] if last else None,
                playthrough_id=next(iter(playthroughs)) if playthroughs else None,
                country_changes=changes,
                cumulative=dict(surviving=sum(r["affairs"]["completed"] for r in last_countries if r["alive"]),
                                extinct_retained=sum(r["affairs"]["completed"] for r in last_countries if not r["alive"])),
                note="Extinct countries are retained separately. Deleted/recreated records may reduce cumulative counters. One run is not a balance conclusion.")


def markdown(report):
    observation = report["observation"]
    lines = ["# 开发测试报告", "", f"- 运行：`{report['run']}`",
        f"- 运行状态：{report['run_state']}；分析状态：{report['analysis_status']}",
        f"- 最后日期：{observation['last_date']}；达到目标：{observation['target_reached']}",
        f"- 检查点完整：{observation['checkpoint_coverage_complete']}",
        f"- 缺少检查点：{', '.join(observation['missing_checkpoints']) or '无'}",
        f"- 引擎总测试结果：{report['engine']['wrapper_status']}",
        f"- 受控状态断言：{report['engine']['controlled_assertions']['status']}",
        f"- 日志分类：{report['diagnostics']['counts']}",
        f"- 崩溃文件数：{len(report['crash_files'])}", "",
        "只有场景明确声明的受控状态断言才会检验。静态检查和视觉验收独立记录。登记诊断与运行报错均保留；日志出现原版路径不代表与模组无关。", "",
        "|日期|存续国家|累计完工（含保留的消亡国家）|存续国家完工|进行中|役负均值|人口（原版千人单位）|",
        "|---|---:|---:|---:|---:|---:|---:|"]
    for row in report["snapshots"]:
        s = row["summary"]
        lines.append("|" + "|".join(str(v) for v in (row["date"], s.get("alive"), s.get("completed_all"),
                     s.get("completed_live"), s.get("active"), s.get("burden_mean"), s.get("population_total"))) + "|")
    lines += ["", "## AI 与项目", "", "可执行月度判定、接受次数和接受率读取被动计数；没有计数时保留为未知，不按零处理。", "",
              "```json", __import__("json").dumps(report["projects"].get("personalities", {}), ensure_ascii=False, indent=2), "```",
              "", "## 异常", ""]
    findings = report["analysis_errors"] + [f"{s['date']}: {a}" for s in report["snapshots"] for a in s["anomalies"]]
    lines += ["- " + f for f in findings] or ["未检测到存档规则异常；仍需结合引擎日志判断。"]
    lines += ["", "完整逐国数据、项目计数和所有日志分组见同名 JSON。单局观察不作为平衡定论。", ""]
    return "\n".join(lines)


def controlled_assertions(snapshot, definitions):
    results = []
    for rule in definitions:
        countries = [c for c in (snapshot or {}).get('countries', []) if c['tag'] == rule['country'] and c['alive']]
        values = countries[0]['variables'] if len(countries) == 1 else {}
        available = len(countries) == 1
        present = rule['variable'] in values
        actual = values.get(rule['variable'])
        passed = available and (not present if rule.get('absent') else present and actual == rule['equals'])
        results.append(dict(name=rule['name'], passed=passed, country_available=available,
                            present=present, actual=actual))
    return dict(status=('passed' if all(r['passed'] for r in results) else 'failed') if results else 'not_run',
                results=results)


def receipt(report):
    """Small reviewable evidence record; large country/log data remains in report.json."""
    observation = {k: v for k, v in report['observation'].items() if k != 'country_changes'}
    hbe_errors = [g for g in report['diagnostics']['groups'] if g['hbe_mentioned'] and g['category'] != 'registration']
    return dict(schema_version=1, kind='run_receipt', generated=report['generated'], run=report['run'],
        version=report['version'], run_state=report['run_state'], analysis_status=report['analysis_status'],
        validation_status=report['validation_status'], observation=observation,
        checkpoint_dates=[r['date'] for r in report['snapshots']], engine=report['engine'],
        log_counts=report['diagnostics']['counts'], hbe_nonregistration_groups=hbe_errors,
        crash_files=report['crash_files'], analysis_errors=report['analysis_errors'])


def analyze_run(run, *, output=None, manifest=None, catalogue=None, baseline=None, cache_dir=None, assertions_from=None):
    run = Path(run).resolve()
    provenance = read_json(run / "provenance.json")
    # Read-only adapter for archived observations; no legacy profile is rewritten.
    scenario = provenance.get("scenario") or dict(checkpoints=provenance["checkpoints"],
        mode="natural" if provenance.get("natural_ai") else "controlled")
    manifest = Path(manifest) if manifest else run / "mod/holy_bashu_empire/build_manifest.json"
    if catalogue is None:
        root = Path(provenance.get("root", Path(__file__).resolve().parents[2]))
        catalogue = read_json(run / 'catalogue.json' if (run / 'catalogue.json').is_file() else root / "data/local_affairs_projects.json")
    elif isinstance(catalogue, (str, Path)):
        catalogue = read_json(catalogue)
    target = Path(output).resolve() if output else run / "analysis"
    target.mkdir(parents=True, exist_ok=True)
    snapshots, errors = [], []
    # Exclude autosaves: they may be overwritten while a live query is running.
    saves = sorted((run / "save games").glob("*.eu5"))
    saves = [p for p in saves if "autosave" not in p.name.casefold()]
    for path in saves:
        try:
            data, cache = load_snapshot(path, manifest=manifest, cache_dir=cache_dir or target / "cache")
            date_key(data.get("date"))
            if not data.get("playthrough_id"):
                raise ValueError("Missing playthrough identity")
            snapshots.append(dict(data, save=str(path), anomalies=anomalies(data), cache=cache))
        except (OSError, ValueError, RuntimeError, SaveError) as exc:
            errors.append(f"{path.name}: {type(exc).__name__}: {exc}")
    try:
        observation = summarize(snapshots, scenario)
    except ValueError:
        # Never produce totals from incompatible playthroughs.
        raise
    snapshots.sort(key=lambda row: date_key(row["date"]))
    status = read_json(run / "status.json") if (run / "status.json").exists() else dict(state="unknown")
    diagnostics = audit(run / "logs", baseline=read_json(baseline) if baseline else None) if (run / "logs").is_dir() else dict(logs_present=False, counts={}, groups=[], files={})
    test_log = (run / "tests.txt").read_text(encoding="utf-8-sig", errors="replace") if (run / "tests.txt").is_file() else ""
    wrappers = re.findall(r"(?im)^.*\b(?:PASS|FAIL)\b.*$", test_log)
    wrapper = "failed" if any(re.search(r"\bFAIL\b", line) for line in wrappers) else "passed" if wrappers else "unknown"
    crashes = [str(p.relative_to(run)) for p in (run / "crashes").rglob("*") if p.is_file() and p.stat().st_size]
    projects = project_summary(snapshots[-1], catalogue) if snapshots else {}
    rules = read_json(assertions_from).get('assertions', []) if assertions_from else scenario.get('assertions', [])
    assertions = controlled_assertions(snapshots[-1] if snapshots else None, rules)
    assertions['source'] = str(assertions_from) if assertions_from else 'frozen scenario'
    assertions['definitions'] = rules
    completion = read_json(run / "completion.json") if (run / "completion.json").exists() else {}
    state = completion.get("state", status["state"])
    # Completion requires dates as well as a successful process, not merely analyzer exit 0.
    if state == "exited":
        state = "completed" if observation["target_reached"] and observation["checkpoint_coverage_complete"] else "incomplete"
    report = dict(schema_version=1, kind="observation", generated=utc_now(), run=str(run),
        version=provenance.get("artifact", {}).get("version", provenance.get("version")),
        scenario=scenario, run_state=state, analysis_status="failed" if errors else "completed",
        observation=observation, snapshots=snapshots, projects=projects,
        diagnostics=diagnostics, engine=dict(wrapper_status=wrapper, result_lines=wrappers,
            controlled_assertions=assertions, static_checks="not_run", visual="not_verified"),
        crash_files=crashes, analysis_errors=errors)
    report['validation_status'] = 'failed' if (wrapper == 'failed' or assertions['status'] == 'failed' or errors or crashes
        or state in ('incomplete', 'process_failed', 'timed_out', 'supervisor_failed', 'analysis_failed')) else 'not_fully_verified'
    write_json(target / "report.json", report)
    (target / "report.md").write_text(markdown(report), encoding="utf-8", newline="\n")
    # Reports on archived runs have no side effects on their saved statuses.
    if "scenario" in provenance and status["state"] not in ("running", "prepared", "preparing"):
        write_json(run / "status.json", dict(state=state, analysis_status=report["analysis_status"],
                    report=str(target / "report.json"), updated=utc_now()))
    return report
