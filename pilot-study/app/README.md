# Android Application Source

This directory contains the Android source and Gradle configuration for the FMCL-CETAS pilot telemetry workload.

## Purpose

The application executes the controlled pilot workload and records the telemetry fields used in the study. The workload and data-collection intent are documented in `../protocol/workload_specification.md`, `../protocol/experimental_protocol.md`, and `../protocol/telemetry_schema.md`.

## Primary source file

The main application implementation is expected at:

```text
src/main/java/com/example/fmclpilot/MainActivity.kt
```

The project should also include the Gradle wrapper and configuration files required to build the application, such as `build.gradle.kts`, `settings.gradle.kts`, `gradle.properties`, `gradlew`, and `gradlew.bat`.

## Build environment

Open this directory in Android Studio or use the Gradle wrapper from a terminal. A compatible Android SDK and the SDK versions declared in the Gradle files are required.

Example PowerShell commands from this directory:

```powershell
.\gradlew.bat tasks
.\gradlew.bat assembleDebug
```

## Source provenance

The reproducibility audit may validate the SHA-256 hash of `MainActivity.kt` against the verified workload source used for the pilot release. If the source is modified, update repository documentation and rerun the relevant analysis/reproduction workflow before treating the modified version as equivalent to the published workload.

## Privacy and release scope

The application source is included for inspection and reproducibility. The public data release must not include unredacted device identifiers, network ports, local timestamps, build fingerprints, charger identifiers, or other restricted telemetry fields. See `../data/raw/README.md` for the release redaction policy.
