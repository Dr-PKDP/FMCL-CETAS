# Anonymized Raw Telemetry Data

This directory contains anonymized sample-level telemetry CSV files supporting
the FMCL-CETAS pilot study.

## File contents

Each released CSV represents one device/run pairing and contains valid,
repeated telemetry observations. The release includes 30 files: three devices
across ten conditions.

The manifest.csv file records each published relative path, device label,
run identifier, imported source-row count, valid telemetry-record count,
observed final elapsed time, source and output SHA-256 checksums, and the
columns removed during redaction.

Blank source metadata placeholders and rows with nonnumeric elapsed time or
sample_ok values other than TRUE are excluded from released telemetry CSVs.
Thus, Figure 4 Panel B and the manifest count valid telemetry observations,
not CSV headers, blank placeholders, operational event logs, or invalid rows.

## Redaction

The following fields are removed before release:

- adb_serial
- adb_tcp_port
- timestamp_local
- build_fingerprint
- charger_id
- dataset_id
- dataset_partition_id
- session_date
- device_manufacturer
- device_model
- android_release
- script_version
- app_version_or_commit
- random_seed

## Important distinction

These files are sample-level telemetry records, not run-event logs. Files that
contain only events such as LOGGER_STARTED, PREFLIGHT_PASSED, and
LOGGER_COMPLETED are operational logs and are not included as the raw
telemetry archive.

## Interpretation

Signed battery current and battery-side power are device-driver dependent.
They should be interpreted within device and should not be pooled as a common
cross-device energy endpoint.

Telemetry coverage is summarized in Table 3 and Figure 4. The released Lenovo
C2-H file contains 78 valid telemetry records and reaches approximately 892
seconds of observed elapsed time.
