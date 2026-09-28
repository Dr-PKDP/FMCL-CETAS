# Telemetry Schema and Interpretation Notes

## Core identifiers and condition metadata

| Field | Definition |
|---|---|
| `device_label` | Study pseudonym for the device |
| `run_id` | Experimental condition identifier, C0 through C5-H |
| `power_state` | Assigned power state: `UNPLUGGED` or `AC_CONNECTED` |
| `workload` | `NONE`, `COMPACT`, or `HIGH` |
| `policy` | `IDLE`, `CONTINUOUS`, or `DUTY_CYCLE` |
| `duty_on_seconds` | Active duration for duty-cycle conditions |
| `duty_off_seconds` | Pause duration for duty-cycle conditions |
| `duration_seconds_requested` | Requested run duration, 900 s |
| `sample_seconds_requested` | Nominal telemetry interval, 10 s |
| `elapsed_seconds` | Elapsed time from run start; the principal time base for analysis |
| `sample_index` | Sequential telemetry-sample index |

## Battery and charging fields

| Field | Unit | Definition |
|---|---:|---|
| `battery_level_percent` | percent | Device-reported battery percentage |
| `battery_temperature_c` | °C | Device-reported battery temperature |
| `battery_voltage_v` | V | Battery voltage after normalization from the raw voltage field |
| `battery_current_now_ma` | mA | Instantaneous battery current after normalization from the raw current field |
| `battery_current_avg_ma` | mA | Device-reported average battery current when available |
| `battery_power_estimate_mw` | mW | Device-reported or derived battery-side power estimate |
| `battery_status_text` | text | Android battery status, such as Charging or Discharging |
| `android_ac_powered` | Boolean | Android AC-power indicator |
| `android_usb_powered` | Boolean | Android USB-power indicator |
| `android_wireless_powered` | Boolean | Android wireless-power indicator |
| `sysfs_ac_online` | 0/1 | Sysfs AC charger indicator when available |
| `sysfs_usb_online` | 0/1 | Sysfs USB charger indicator when available |
| `sysfs_charger_online` | 0/1 | Sysfs charger indicator when available |

## CPU and thermal fields

| Field | Unit | Definition |
|---|---:|---|
| `cpu_busy_percent` | percent | CPU non-idle fraction calculated from CPU tick deltas |
| `cpu_*_delta_ticks` | ticks | CPU-state tick deltas used to derive busy percentage |
| `thermal_cpu_c` | °C | Thermal-service CPU temperature where available |
| `thermal_gpu_c` | °C | Thermal-service GPU temperature where available |
| `thermal_battery_c` | °C | Thermal-service battery temperature where available |
| `thermal_skin_c` | °C | Thermal-service skin temperature where available |
| `thermal_status` | integer | Android thermal status where available |
| `thermal_status_name` | text | Human-readable Android thermal status |

## Data-quality fields

| Field | Definition |
|---|---|
| `sample_ok` | Indicates whether the logger considered the sample valid |
| `sample_error` | Captured logger error text, if present |

## Derived outcomes

Run-level results use valid observations from 60 s through the final valid telemetry record. Key derived outcomes are:

\[
\Delta B = B_{\mathrm{final}} - B_{\mathrm{initial}}
\]

where \(\Delta B\) is battery-level change in percentage points.

\[
\Delta T = T_{\mathrm{final}} - T_{\mathrm{initial}}
\]

where \(\Delta T\) is battery-temperature change in degrees Celsius.

For duty-cycle conditions, phase contrasts use:

\[
\Delta X_{\mathrm{active-pause}} = \overline{X}_{\mathrm{active}} - \overline{X}_{\mathrm{pause}}
\]

where positive values indicate a higher mean during active phases.

## Interpretation limitation

Signed battery current and battery-side power are device-driver dependent. In this study, Lenovo and Motorola exhibited negative signed values under unplugged conditions and positive values under AC-connected conditions; Oppo showed the reverse sign orientation. Signed current and power must therefore be interpreted within device. Do not pool or rank their signed values as a common cross-device energy endpoint.
