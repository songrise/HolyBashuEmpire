"""Archive selected evidence; never delete profiles, caches or player data."""
from pathlib import Path
import zipfile

from .common import within


def archive(run, output, *, saves=False):
    run, output = Path(run).resolve(), Path(output).resolve()
    if output == run or run in output.parents:
        raise ValueError("Archive must be outside the run directory")
    if output.exists():
        raise FileExistsError(output)
    patterns = ["provenance.json", "catalogue.json", "status.json", "completion.json", "launch.json", "process.json",
                "stop-request.json", "tests.txt", "*stdout.txt", "*stderr.txt", "logs/error*.log",
                "analysis/report.json", "analysis/report.md"]
    if saves:
        patterns.append("save games/*.eu5")
    selected = sorted({within(run, p) for pattern in patterns for p in run.glob(pattern) if p.is_file()})
    if not selected:
        raise ValueError("No run evidence found")
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, "x", compression=zipfile.ZIP_DEFLATED, compresslevel=1) as bundle:
        for path in selected:
            bundle.write(path, path.relative_to(run).as_posix())
    with zipfile.ZipFile(output) as bundle:
        failure = bundle.testzip()
        if failure:
            raise ValueError("Archive CRC verification failed: " + failure)
    return dict(path=str(output), file_count=len(selected), bytes=output.stat().st_size,
                source_deleted=False, includes_saves=saves)
