# Analysis Definitions

This document defines the released pilot-study calculations. All derived summaries should use these definitions so that raw telemetry, processed tables, figures, and manuscript text remain consistent.

## Valid telemetry record

A telemetry record is valid when:

1. `elapsed_seconds` is numeric; and
2. `sample_ok` is `TRUE` when that field is present.

For temperature summaries, `battery_temperature_c` must additionally be numeric. Blank metadata placeholders, event-log records, failed samples, and rows without numeric elapsed time are excluded.

## Coverage measures

- **Valid telemetry records:** number of valid telemetry records in a device/run file.
- **Observed elapsed time:** maximum `elapsed_seconds` among valid telemetry records in that file.
- **Lenovo C0:** 90 valid records and 890 seconds observed elapsed time after exclusion of one blank source placeholder row.
- **Lenovo C2-H:** 78 valid records and approximately 892 seconds observed elapsed time.

## Temperature measures

For each retained device/run file, using all valid temperature records:

- **Minimum temperature:** minimum `battery_temperature_c`.
- **Mean temperature:** arithmetic mean of `battery_temperature_c`.
- **Maximum temperature:** maximum `battery_temperature_c`.
- **Within-run temperature change:** final valid `battery_temperature_c` minus initial valid `battery_temperature_c`.

The signed within-run change is written as:

\[
\Delta T_{d,r} = T_{\mathrm{final},d,r} - T_{\mathrm{initial},d,r}.
\]

It is not interchangeable with the within-file temperature span:

\[
T_{\max,d,r} - T_{\min,d,r}.
\]

## Table 3 definitions

For each condition, Table 3 reports:

- **Median device-level maximum battery temperature:** the median of the three device-level maximum battery temperatures.
- **Observed battery-temperature range across valid samples:** the minimum to maximum temperature across all valid temperature samples from the three retained device/run files.

Table 3 is descriptive. Because historical runs were sequenced and did not necessarily begin from matched thermal states, condition-level absolute temperatures are not interpreted as a causal estimate of the separate effect of charging state or workload.

## CPU-busy measure

When reported, mean CPU busy is the arithmetic mean of numeric `cpu_busy_percent` values among valid telemetry records. Missing CPU-busy values are excluded from the CPU-busy mean only. A missing first CPU-busy value is expected when CPU utilization requires a preceding tick interval.

## Battery-level change

When reported, battery-level change is calculated within device/run as:

\[
\Delta B_{d,r} = B_{\mathrm{final},d,r} - B_{\mathrm{initial},d,r},
\]

where the initial and final values are the first and last valid numeric `battery_level_percent` observations. Units are percentage points.

## Battery current and power

Battery current, voltage, and battery-side power are device- and driver-dependent telemetry fields. They are not pooled across devices and are not used as a common cross-device quantitative energy endpoint. Any device-specific reporting must retain the original sign convention, state the raw/conversion rule, and be qualified by the availability and unit-semantics limitations of Android-exposed battery properties.

## Duty-cycle phases

The released application source implements a programmed duty cycle of 60 seconds active followed by 30 seconds pause. Unless a separate analysis explicitly validates a different boundary source, phase assignment follows this pre-specified schedule. Operator-entered event logs are ancillary operational records and do not provide application-instrumented elapsed-time phase boundaries.
