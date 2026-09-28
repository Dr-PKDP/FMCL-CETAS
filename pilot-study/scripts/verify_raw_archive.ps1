[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$RepositoryRoot
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$RawDirectory = Join-Path $RepositoryRoot "data\raw"
$ManifestPath = Join-Path $RawDirectory "manifest.csv"
$ExpectedDevices = @("oppo_a78_5g", "lenovo_tablet", "motorola_device")
$ExpectedRuns = @("C0", "C1", "C2-L", "C2-H", "C3-L", "C3-H", "C4-L", "C4-H", "C5-L", "C5-H")
$RestrictedColumns = @(
    "adb_serial",
    "adb_tcp_port",
    "timestamp_local",
    "build_fingerprint",
    "charger_id",
    "dataset_id",
    "dataset_partition_id"
)

function Normalize-Name {
    param([string]$Name)

    if ($null -eq $Name) {
        return ""
    }

    return (($Name -replace "[^A-Za-z0-9]", "").ToLowerInvariant())
}

function Find-ColumnName {
    param(
        [string[]]$Columns,
        [string[]]$Candidates
    )

    foreach ($candidate in $Candidates) {
        $target = Normalize-Name $candidate
        foreach ($column in $Columns) {
            if ((Normalize-Name $column) -eq $target) {
                return $column
            }
        }
    }

    return $null
}

function Normalize-Device {
    param([string]$Value)

    if ($null -eq $Value) {
        return ""
    }

    $compact = Normalize-Name $Value

    switch ($compact) {
        "oppoa785g" { return "oppo_a78_5g" }
        "oppoa78" { return "oppo_a78_5g" }
        "lenovotablet" { return "lenovo_tablet" }
        "lenovo" { return "lenovo_tablet" }
        "tablet" { return "lenovo_tablet" }
        "motoroladevice" { return "motorola_device" }
        "motorola" { return "motorola_device" }
        default { return (($Value.Trim().ToLowerInvariant()) -replace "[-\s]+", "_") }
    }
}

function Normalize-Run {
    param([string]$Value)

    if ($null -eq $Value) {
        return ""
    }

    $text = (($Value.Trim().ToUpperInvariant()) -replace "_", "-" -replace "\s+", "")

    if ($text -match "^(C[0-5])([LH])$") {
        return "$($Matches[1])-$($Matches[2])"
    }

    return $text
}

function Convert-ToInvariantDouble {
    param([object]$Value)

    $number = 0.0
    if ([double]::TryParse(
        ([string]$Value),
        [System.Globalization.NumberStyles]::Float,
        [System.Globalization.CultureInfo]::InvariantCulture,
        [ref]$number
    )) {
        return $number
    }

    return $null
}

function Get-ValidRows {
    param(
        [object[]]$Rows,
        [string]$ElapsedColumn,
        [string]$SampleOkColumn
    )

    $valid = @()

    foreach ($row in $Rows) {
        $elapsed = Convert-ToInvariantDouble $row.$ElapsedColumn
        if ($null -eq $elapsed) {
            continue
        }

        if ($null -ne $SampleOkColumn) {
            $sampleOk = ([string]$row.$SampleOkColumn).Trim().ToUpperInvariant()
            if ($sampleOk -ne "TRUE") {
                continue
            }
        }

        $valid += $row
    }

    return @($valid)
}

if (-not (Test-Path -LiteralPath $RawDirectory -PathType Container)) {
    throw "Raw-data directory not found: $RawDirectory"
}

if (-not (Test-Path -LiteralPath $ManifestPath -PathType Leaf)) {
    throw "Raw-data manifest not found: $ManifestPath"
}

$telemetryFiles = @(
    Get-ChildItem -LiteralPath $RawDirectory -Recurse -File -Filter "*_telemetry.csv" |
    Sort-Object FullName
)

if ($telemetryFiles.Count -ne 30) {
    throw "Expected 30 released telemetry CSV files; found $($telemetryFiles.Count)."
}

$summary = @()

foreach ($file in $telemetryFiles) {
    $rows = @(Import-Csv -LiteralPath $file.FullName)

    if ($rows.Count -le 10) {
        throw "Telemetry file is implausibly short: $($file.FullName) ($($rows.Count) rows)."
    }

    $columns = @($rows[0].PSObject.Properties.Name)
    $restrictedPresent = @($RestrictedColumns | Where-Object { $columns -contains $_ })

    if ($restrictedPresent.Count -gt 0) {
        throw (
            "Restricted fields remain in $($file.FullName): " +
            ($restrictedPresent -join ", ")
        )
    }

    $deviceColumn = Find-ColumnName -Columns $columns -Candidates @("device_label", "deviceLabel")
    $runColumn = Find-ColumnName -Columns $columns -Candidates @("run_id", "runId")
    $elapsedColumn = Find-ColumnName -Columns $columns -Candidates @("elapsed_seconds", "elapsedSeconds")
    $sampleOkColumn = Find-ColumnName -Columns $columns -Candidates @("sample_ok", "sampleOk")
    $temperatureColumn = Find-ColumnName -Columns $columns -Candidates @("battery_temperature_c", "batteryTemperatureC")

    if ($null -eq $deviceColumn -or $null -eq $runColumn -or $null -eq $elapsedColumn) {
        throw "Required device/run/elapsed fields are missing in: $($file.FullName)"
    }

    if ($null -eq $temperatureColumn) {
        throw "battery_temperature_c is missing in: $($file.FullName)"
    }

    $validRows = @(Get-ValidRows -Rows $rows -ElapsedColumn $elapsedColumn -SampleOkColumn $sampleOkColumn)

    if ($validRows.Count -le 10) {
        throw "Too few valid telemetry rows in: $($file.FullName)"
    }

    $first = $validRows | Select-Object -First 1
    $device = Normalize-Device ([string]$first.$deviceColumn)
    $run = Normalize-Run ([string]$first.$runColumn)

    if ($ExpectedDevices -notcontains $device) {
        throw "Unexpected device label '$device' in: $($file.FullName)"
    }

    if ($ExpectedRuns -notcontains $run) {
        throw "Unexpected run ID '$run' in: $($file.FullName)"
    }

    $elapsedValues = @()
    foreach ($row in $validRows) {
        $elapsed = Convert-ToInvariantDouble $row.$elapsedColumn
        if ($null -ne $elapsed) {
            $elapsedValues += $elapsed
        }
    }

    $summary += [PSCustomObject]@{
        device_label            = $device
        run_id                  = $run
        valid_telemetry_records = $validRows.Count
        observed_elapsed_seconds = [double](($elapsedValues | Measure-Object -Maximum).Maximum)
        relative_path           = $file.FullName.Substring($RawDirectory.Length).TrimStart("\") -replace "\\", "/"
        published_sha256        = (Get-FileHash -LiteralPath $file.FullName -Algorithm SHA256).Hash
    }
}

if ($summary.Count -ne 30) {
    throw "Expected 30 verified telemetry summaries; found $($summary.Count)."
}

if ($summary | Group-Object device_label, run_id | Where-Object { $_.Count -ne 1 }) {
    throw "Duplicate device/run combinations were found in released raw telemetry."
}

foreach ($device in $ExpectedDevices) {
    foreach ($run in $ExpectedRuns) {
        $match = @($summary | Where-Object { $_.device_label -eq $device -and $_.run_id -eq $run })
        if ($match.Count -ne 1) {
            throw "Missing or duplicate raw telemetry file for $device / $run."
        }
    }
}

$lenovoC0 = @($summary | Where-Object { $_.device_label -eq "lenovo_tablet" -and $_.run_id -eq "C0" })
$lenovoC2H = @($summary | Where-Object { $_.device_label -eq "lenovo_tablet" -and $_.run_id -eq "C2-H" })

if ($lenovoC0[0].valid_telemetry_records -ne 90) {
    throw "Lenovo C0 must contain 90 valid telemetry records; found $($lenovoC0[0].valid_telemetry_records)."
}

if ($lenovoC2H[0].valid_telemetry_records -ne 78) {
    throw "Lenovo C2-H must contain 78 valid telemetry records; found $($lenovoC2H[0].valid_telemetry_records)."
}

$manifest = @(Import-Csv -LiteralPath $ManifestPath)
if ($manifest.Count -ne 30) {
    throw "manifest.csv must contain 30 rows; found $($manifest.Count)."
}

$manifestColumns = @($manifest[0].PSObject.Properties.Name)
$manifestDeviceColumn = Find-ColumnName -Columns $manifestColumns -Candidates @("device_label")
$manifestRunColumn = Find-ColumnName -Columns $manifestColumns -Candidates @("run_id")
$manifestRecordsColumn = Find-ColumnName -Columns $manifestColumns -Candidates @("valid_telemetry_records", "records")
$manifestElapsedColumn = Find-ColumnName -Columns $manifestColumns -Candidates @("final_elapsed_seconds", "observed_elapsed_seconds")
$manifestHashColumn = Find-ColumnName -Columns $manifestColumns -Candidates @("published_sha256")

if ($null -eq $manifestDeviceColumn -or $null -eq $manifestRunColumn) {
    throw "manifest.csv lacks required device_label/run_id columns."
}

foreach ($row in $manifest) {
    $device = Normalize-Device ([string]$row.$manifestDeviceColumn)
    $run = Normalize-Run ([string]$row.$manifestRunColumn)
    $match = @($summary | Where-Object { $_.device_label -eq $device -and $_.run_id -eq $run })

    if ($match.Count -ne 1) {
        throw "Manifest row does not map to exactly one raw telemetry file: $device / $run"
    }

    if ($null -ne $manifestRecordsColumn) {
        $records = Convert-ToInvariantDouble $row.$manifestRecordsColumn
        if ($null -eq $records -or [int]$records -ne $match[0].valid_telemetry_records) {
            throw "Manifest valid-record mismatch for $device / $run."
        }
    }

    if ($null -ne $manifestElapsedColumn) {
        $elapsed = Convert-ToInvariantDouble $row.$manifestElapsedColumn
        if ($null -eq $elapsed -or [math]::Abs($elapsed - $match[0].observed_elapsed_seconds) -gt 0.11) {
            throw "Manifest elapsed-time mismatch for $device / $run."
        }
    }

    if ($null -ne $manifestHashColumn) {
        $hash = ([string]$row.$manifestHashColumn).Trim()
        if ($hash -and $hash -ne $match[0].published_sha256) {
            throw "Manifest SHA-256 mismatch for $device / $run."
        }
    }
}

Write-Host "RAW ARCHIVE VERIFICATION: PASS" -ForegroundColor Green
Write-Host "Telemetry files: 30"
Write-Host "Manifest rows: 30"
Write-Host "Lenovo C0: 90 valid records; $($lenovoC0[0].observed_elapsed_seconds) s"
Write-Host "Lenovo C2-H: 78 valid records; $($lenovoC2H[0].observed_elapsed_seconds) s"
Write-Host ""

$summary |
    Sort-Object device_label, run_id |
    Select-Object device_label, run_id, valid_telemetry_records, observed_elapsed_seconds, relative_path |
    Format-Table -AutoSize
