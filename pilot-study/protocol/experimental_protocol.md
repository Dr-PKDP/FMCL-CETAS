# Experimental Protocol

## Objective

This protocol characterizes battery, thermal, and CPU-utilization behavior during local machine-learning training on three Android devices. It was designed to extend beyond a simple binary stress test by independently varying assigned power state, workload intensity, and execution policy.

## Devices and conditions

Three Android devices completed the requested experimental conditions:

- Oppo A78 5G
- Lenovo tablet
- Motorola device

Each condition was requested for 900 s with nominal 10-s telemetry sampling. The display remained on and Battery Saver remained off. Assigned power state was manipulated by charger plug/unplug events rather than by a USB data connection.

## Experimental conditions

| Run | Assigned power state | Workload | Policy | Active interval | Pause interval |
|---|---|---|---|---:|---:|
| C0 | Unplugged | None | Idle | — | — |
| C1 | AC-connected | None | Idle | — | — |
| C2-L | AC-connected | Compact | Continuous | Continuous | — |
| C2-H | AC-connected | High | Continuous | Continuous | — |
| C3-L | Unplugged | Compact | Continuous | Continuous | — |
| C3-H | Unplugged | High | Continuous | Continuous | — |
| C4-L | AC-connected | Compact | Duty cycle | 60 s | 30 s |
| C4-H | AC-connected | High | Duty cycle | 60 s | 30 s |
| C5-L | Unplugged | Compact | Duty cycle | 60 s | 30 s |
| C5-H | Unplugged | High | Duty cycle | 60 s | 30 s |

## Workload rationale

The workload was intentionally CPU-dominant and software-portable. It used local neural-network training implemented with scalar array operations rather than device-specific GPU or neural-processing APIs. GPU and NPU stressors were excluded because hardware availability, driver behavior, thermal pathways, and telemetry support vary substantially across Android devices, reducing the comparability of a common protocol.

Compact and High workload levels were included to evaluate intensity dependence rather than only a binary idle-versus-stress contrast. Compact represented a lower, sustained local-training configuration. High increased synthetic-data volume, network dimensionality, and training epochs per round. Continuous and duty-cycle policies were included to compare sustained computational demand with periodically interrupted demand while retaining the same computational task and workload level.

The 60-s active/30-s pause schedule yields a 90-s cycle with a 66.7% active fraction. The active duration allows multiple local-training rounds to execute; the pause duration creates a distinct lower-demand phase without dividing the experiment into separate recording sessions. A requested 900-s run contains ten nominal duty cycles.

## Telemetry acquisition

At each sampling point, the telemetry logger recorded available battery state, battery temperature, voltage, current-related fields, battery-side power, charging-state indicators, CPU busy percentage, and thermal-service measurements. It also recorded condition metadata and elapsed time.

## Analysis windows

The prespecified run-level analysis window begins at 60 s and extends through the final valid record. The first 60 s are excluded from summary statistics to reduce workload-startup and charger-transition effects.

For duty-cycle phase analysis, phase classification uses elapsed time modulo 90 s:

- Active phase: offsets 0-59 s.
- Pause phase: offsets 60-89 s.

For a metric \(X\), the active-minus-pause contrast is:

\[
\Delta X_{\mathrm{active-pause}} = \overline{X}_{\mathrm{active}} - \overline{X}_{\mathrm{pause}}.
\]

Positive values indicate higher mean values during the active phase.

## File retention

Candidate telemetry CSV files must contain device label, run identifier, elapsed time, and the fields required for the intended analysis. If duplicate exports exist for the same device/run condition, retain the file with the greatest valid elapsed-time coverage. Do not merge partial files, interpolate missing records, or reconstruct unavailable telemetry.
