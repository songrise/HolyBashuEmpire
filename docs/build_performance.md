# Build snapshot batching

The full builder defers intermediate `snapshot_files()` calls for its output
directory and forces a complete snapshot before writing the final manifest.
Standalone stages retain eager snapshots. The context is restored on exceptions;
snapshots of other directories are unaffected.

Intermediate manifests inside this context have an empty `files` map. Stages
must not use that map to decide which files exist or need processing. Read the
filesystem for those decisions. A failed full build is not a publishable package;
only the successfully finalized manifest contains its complete inventory.

The initial inline inventory is deliberately retained: `apply_observer_hotfix`
currently discovers the legacy hash mapping from its contents. Removing that
inventory requires first replacing this implicit dependency. There are therefore
two complete inventories in a full build, not one.

`write_preserving_format()` compares the encoded output with the existing bytes
before writing. It preserves the previous encoding/BOM and newline conversion,
including legacy mixed-newline behavior. Identical writes do not touch the file.
This does not cover independent `write_text()` calls or image exporters.

## Validation

Run helper regressions from the repository root:

```console
python -m unittest discover -s tools -p test_build_support.py
```

For pipeline changes, build the baseline and candidate into separate clean output
directories using identical source data and game files. Compare every relative
filename and SHA-256, including `build_manifest.json`, then run `validate_mod.py`
on the candidate. Some build stages also write source-side generated data:
use isolated source copies for timing and comparison.

On 2026-10-21, the isolated trial produced identical bytes for all 803 files and
passed 4,703 structural checks. One unprofiled sequential timing pair measured:

| Measurement | Baseline | Candidate |
| --- | ---: | ---: |
| Full build | 83.54 s | 54.81 s |
| Public snapshot calls, cumulative | 16.98 s | 1.31 s |

The wall-time reduction was 34.4%; cache/order and machine load affect this single
pair. It is not a cold-cache benchmark or a guaranteed speedup. The initial inline
inventory is not included in the public snapshot timing.

Next priorities are repeated script parsing and flag pixel processing. Persistent
hash caching and parallel hashing have lower value after removing repeated scans.
Any further optimization must retain output-byte equivalence.
