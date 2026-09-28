param(
    [Parameter(Mandatory = $true)][string]$DeviceLabel,
    [Parameter(Mandatory = $true)][string]$Serial,
    [Parameter(Mandatory = $true)][ValidateSet("C0","C1","C2-L","C2-H","C3-L","C3-H","C4-L","C4-H","C5-L","C5-H")][string]$RunId,
    [Parameter(Mandatory = $true)][ValidateSet("UNPLUGGED","AC_CONNECTED")][string]$PowerState,
    [Parameter(Mandatory = $true)][ValidateSet("NONE","COMPACT","HIGH")][string]$Workload,
    [Parameter(Mandatory = $true)][ValidateSet("IDLE","CONTINUOUS","DUTY_CYCLE")][string]$Policy,
    [Parameter(Mandatory = $true)][int]$DurationSeconds,
    [int]$SampleSeconds = 10
)

$ErrorActionPreference = "Stop"

$adb = "$env:LOCALAPPDATA\Android\Sdk\platform-tools\adb.exe"
if (-not (Test-Path $adb)) { throw "adb.exe not found: $adb" }

$runStart = Get-Date
$sessionDate = $runStart.ToString("yyyyMMdd")
$sessionTime = $runStart.ToString("HHmmss")
$deviceSafe = ($DeviceLabel -replace '[^A-Za-z0-9_-]', '_')
$runSafe = ($RunId -replace '[^A-Za-z0-9_-]', '_')

$outDir = Join-Path $PSScriptRoot "logs\final_telemetry\$sessionDate\$deviceSafe"
New-Item -ItemType Directory -Path $outDir -Force | Out-Null

$baseName = "{0}_{1}_{2}_{3}" -f $sessionDate,$sessionTime,$deviceSafe,$runSafe
$csvPath = Join-Path $outDir "$baseName`_telemetry.csv"
$metaPath = Join-Path $outDir "$baseName`_metadata.txt"

$headers = @(
    "session_date","run_id","device_label","adb_serial",
    "power_state","workload","policy",
    "timestamp_local","elapsed_seconds",
    "level_percent","status",
    "temperature_raw_tenths_c","temperature_c",
    "voltage_raw_mv","voltage_v",
    "current_now_raw_ua","current_now_ma",
    "current_avg_raw_ua","current_avg_ma",
    "charge_counter_raw_uah",
    "battery_present",
    "sample_ok","sample_error"
)

$headers -join "," | Set-Content -Path $csvPath -Encoding ascii

@(
    "session_date=$sessionDate"
    "run_id=$RunId"
    "device_label=$DeviceLabel"
    "adb_serial=$Serial"
    "power_state=$PowerState"
    "workload=$Workload"
    "policy=$Policy"
    "duration_seconds=$DurationSeconds"
    "sample_seconds=$SampleSeconds"
    "started_local=$($runStart.ToString('yyyy-MM-dd HH:mm:ss'))"
    "csv_path=$csvPath"
) | Set-Content -Path $metaPath -Encoding ascii

function Get-PropValue {
    param([string]$Name)
    $v = (& $adb -s $Serial shell getprop $Name 2>$null | Out-String).Trim()
    return $v
}

function Get-BatteryValue {
    param([string]$Pattern)
    $line = (& $adb -s $Serial shell dumpsys battery 2>$null | Select-String -Pattern $Pattern | Select-Object -First 1 | ForEach-Object { $_.Line.Trim() })
    if ([string]::IsNullOrWhiteSpace($line)) { return "" }
    return (($line -split ":",2)[1]).Trim()
}

function To-CultureInvariantNumber {
    param($Value)
    if ([string]::IsNullOrWhiteSpace("$Value")) { return "" }
    return "$Value".Trim()
}

function Write-CsvRow {
    param([hashtable]$Row)
    $values = foreach ($h in $headers) {
        $v = if ($Row.ContainsKey($h)) { "$($Row[$h])" } else { "" }
        '"' + $v.Replace('"','""') + '"'
    }
    Add-Content -Path $csvPath -Value ($values -join ",") -Encoding ascii
}

Write-Host "PREFLIGHT: checking $Serial ..."
$deviceState = (& $adb -s $Serial get-state 2>$null | Out-String).Trim()
if ($deviceState -ne "device") { throw "ADB target is not ready: $Serial ($deviceState)" }

$preLevel = Get-BatteryValue '^\s*level:'
$preStatus = Get-BatteryValue '^\s*status:'
$preTemp = Get-BatteryValue '^\s*temperature:'

if ($preLevel -notmatch '^\d+$' -or $preStatus -notmatch '^\d+$' -or $preTemp -notmatch '^\d+$') {
    throw "PREFLIGHT FAILED: level/status/temperature are not numeric."
}

Write-Host "PREFLIGHT PASSED."
Write-Host "CSV: $csvPath"
Write-Host "Run: $RunId | $PowerState | $Workload | $Policy | $DurationSeconds s"

$stopwatch = [System.Diagnostics.Stopwatch]::StartNew()
$failures = 0

while ($stopwatch.Elapsed.TotalSeconds -lt $DurationSeconds) {
    $elapsed = [math]::Floor($stopwatch.Elapsed.TotalSeconds)
    $stamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"

    try {
        $state = (& $adb -s $Serial get-state 2>$null | Out-String).Trim()
        if ($state -ne "device") { throw "adb state=$state" }

        $level = Get-BatteryValue '^\s*level:'
        $status = Get-BatteryValue '^\s*status:'
        $tempRaw = Get-BatteryValue '^\s*temperature:'
        $voltageRaw = Get-BatteryValue '^\s*voltage:'
        $present = Get-BatteryValue '^\s*present:'

        $currentNowRaw = Get-PropValue "sys.battery.current_now"
        if ([string]::IsNullOrWhiteSpace($currentNowRaw)) { $currentNowRaw = Get-PropValue "battery.current_now" }

        $currentAvgRaw = Get-PropValue "sys.battery.current_avg"
        if ([string]::IsNullOrWhiteSpace($currentAvgRaw)) { $currentAvgRaw = Get-PropValue "battery.current_avg" }

        $chargeCounterRaw = Get-PropValue "sys.battery.charge_counter"
        if ([string]::IsNullOrWhiteSpace($chargeCounterRaw)) { $chargeCounterRaw = Get-PropValue "battery.charge_counter" }

        $tempC = ""
        if ($tempRaw -match '^-?\d+$') {
            $tempC = ([int]$tempRaw / 10.0).ToString("0.0",[cultureinfo]::InvariantCulture)
        }

        $voltageV = ""
        if ($voltageRaw -match '^-?\d+$') {
            $v = [double]$voltageRaw
            if ($v -gt 100000) { $v = $v / 1000000.0 }
            elseif ($v -gt 1000) { $v = $v / 1000.0 }
            $voltageV = $v.ToString("0.000",[cultureinfo]::InvariantCulture)
        }

        $currentNowMa = ""
        if ($currentNowRaw -match '^-?\d+$') {
            $currentNowMa = ([double]$currentNowRaw / 1000.0).ToString("0.000",[cultureinfo]::InvariantCulture)
        }

        $currentAvgMa = ""
        if ($currentAvgRaw -match '^-?\d+$') {
            $currentAvgMa = ([double]$currentAvgRaw / 1000.0).ToString("0.000",[cultureinfo]::InvariantCulture)
        }

        if ($level -notmatch '^\d+$' -or $status -notmatch '^\d+$' -or $tempRaw -notmatch '^-?\d+$') {
            throw "non-numeric required field(s): level=$level status=$status temp=$tempRaw"
        }

        Write-CsvRow @{
            session_date = $sessionDate
            run_id = $RunId
            device_label = $DeviceLabel
            adb_serial = $Serial
            power_state = $PowerState
            workload = $Workload
            policy = $Policy
            timestamp_local = $stamp
            elapsed_seconds = $elapsed
            level_percent = $level
            status = $status
            temperature_raw_tenths_c = $tempRaw
            temperature_c = $tempC
            voltage_raw_mv = $voltageRaw
            voltage_v = $voltageV
            current_now_raw_ua = $currentNowRaw
            current_now_ma = $currentNowMa
            current_avg_raw_ua = $currentAvgRaw
            current_avg_ma = $currentAvgMa
            charge_counter_raw_uah = $chargeCounterRaw
            battery_present = $present
            sample_ok = "TRUE"
            sample_error = ""
        }

        $failures = 0
        Write-Host "t=$elapsed s | level=$level% | status=$status | temp=$tempC C | voltage=$voltageV V | current_now=$currentNowMa mA"
    }
    catch {
        $failures++
        $message = $_.Exception.Message.Replace('"',"'")

        Write-CsvRow @{
            session_date = $sessionDate
            run_id = $RunId
            device_label = $DeviceLabel
            adb_serial = $Serial
            power_state = $PowerState
            workload = $Workload
            policy = $Policy
            timestamp_local = $stamp
            elapsed_seconds = $elapsed
            sample_ok = "FALSE"
            sample_error = $message
        }

        Write-Warning "Sample failed at $elapsed s: $message"

        if ($failures -ge 2) {
            throw "Two consecutive samples failed. CSV retained as incomplete: $csvPath"
        }
    }

    $next = ($elapsed + $SampleSeconds) - $stopwatch.Elapsed.TotalSeconds
    if ($next -gt 0) { Start-Sleep -Seconds $next }
}

$stopwatch.Stop()
$data = Import-Csv $csvPath
$good = @($data | Where-Object {
    $_.sample_ok -eq "TRUE" -and
    $_.level_percent -match '^\d+$' -and
    $_.status -match '^\d+$' -and
    $_.temperature_c -match '^-?\d+(\.\d+)?$'
})

Write-Host ""
Write-Host "RUN COMPLETE"
Write-Host "CSV: $csvPath"
Write-Host "Rows: $($data.Count)"
Write-Host "Valid core telemetry rows: $($good.Count)"
Write-Host "Final elapsed seconds: $($data[-1].elapsed_seconds)"
Write-Host "Required core fields: level, status, temperature"
