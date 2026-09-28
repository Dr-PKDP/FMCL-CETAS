# Source and Build Provenance

## Released application source

The released Android application source is located at:

```text
../app/src/main/java/com/example/fmclpilot/MainActivity.kt
```

It implements the local-training workload selector and the continuous and duty-cycle policies used in the pilot protocol. The duty-cycle implementation is configured for a 60-second active interval followed by a 30-second pause interval.

The application source defines two synthetic local-training configurations:

| Workload | Input features | Hidden units | Classes | Samples | Local epochs | Trainable parameters |
|---|---:|---:|---:|---:|---:|---:|
| Compact | 32 | 32 | 4 | 2,000 | 5 | 1,188 |
| High-load | 64 | 64 | 4 | 8,000 | 10 | 4,420 |

The parameter count includes both affine-layer weights and biases:

\[
(\mathrm{features} \times \mathrm{hidden}) + \mathrm{hidden} + (\mathrm{classes} \times \mathrm{hidden}) + \mathrm{classes}.
\]

## Historical-run provenance limitation

The released source is compatible with the pilot protocol, including the continuous and programmed duty-cycle modes. However, the retained historical telemetry archive does not contain a per-run APK hash, package version code, Git commit identifier, source checksum, or cryptographic build identifier.

Accordingly, the exact build provenance of each historical run, including C2 and C3 runs, cannot be independently verified from the released telemetry records alone. The repository should not claim a cryptographically verified one-to-one link between every historical telemetry file and the released source snapshot.

## Telemetry acquisition source

The repository includes the telemetry-acquisition script under `../scripts/` where released. The acquisition workflow records run-relative `elapsed_seconds` using a local stopwatch and records wall-clock timestamps for acquisition diagnostics. Reproducible within-run analyses use `elapsed_seconds`, not wall-clock timestamps.

## Scope of reproducibility

The repository supports verification of the released anonymized telemetry archive and regeneration of the released pilot-study derived outputs. It does not recreate the historical device acquisitions, establish exact historical APK identity, or reproduce undocumented development history.
