# Event-Log Policy

## Purpose

Per-run event CSV files may be retained under `../data/events/` as ancillary operational documentation. They are separate from the sample-level telemetry archive in `../data/raw/`.

## Event fields

The operator-event workflow can record:

```text
session_date
run_id
device_label
timestamp_local
elapsed_seconds
event_type
training_phase
duty_cycle_index
details
```

Supported event types include `TRAINING_STARTED`, `TRAINING_PAUSED`, `TRAINING_RESUMED`, `TRAINING_COMPLETED`, `INTERRUPTION`, `ERROR`, and `NOTE`. Supported phase labels include `IDLE`, `TRAINING_ON`, `PAUSE`, `COMPLETE`, and `UNKNOWN`.

## Interpretation limitations

These event records are operator-entered. `timestamp_local` is a PC wall-clock timestamp written when the event utility is invoked. The `elapsed_seconds` field may contain the marker `OPERATOR_TIMESTAMP` rather than an automatically measured run-relative elapsed time.

Therefore, event records:

- Document selected operational start, pause, resume, completion, interruption, error, and note events.
- Can help identify completed and interrupted attempts when duplicate files exist.
- Do not constitute application-instrumented or automatically synchronized duty-cycle phase-boundary measurements.
- Are not the authoritative source for raw telemetry timing, telemetry coverage, or within-run trajectories.

## Analytical use

Unless a separate analysis explicitly demonstrates reliable synchronization and complete transition logging, duty-cycle phase assignment follows the released application's pre-specified 60-second active / 30-second pause schedule. The sample-level telemetry CSV `elapsed_seconds` field remains the canonical time coordinate for within-run temperature and coverage analyses.

## Release guidance

If event logs are released, preserve only the event files that correspond to retained telemetry runs. Keep interrupted/abandoned attempts only when clearly labeled as such. Remove or redact identifiers and local timestamps when necessary under the repository's data-release policy.
