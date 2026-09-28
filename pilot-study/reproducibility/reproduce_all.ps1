[CmdletBinding()]
param(
    [switch]$SkipPythonInstall,
    [switch]$SkipChecksumManifest
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$RepositoryRoot = Split-Path -Parent $PSScriptRoot
$ScriptsDirectory = Join-Path $RepositoryRoot "scripts"
$RawDirectory = Join-Path $RepositoryRoot "data\raw"
$ProcessedDirectory = Join-Path $RepositoryRoot "data\processed"
$ResultsDirectory = Join-Path $RepositoryRoot "results"
$ReproducibilityDirectory = $PSScriptRoot

function Write-Stage {
    param([string]$Message)
    Write-Host "" 
    Write-Host "=== $Message ===" -ForegroundColor Cyan
}

function Require-Path {
    param(
        [string]$Path,
        [string]$Description
    )

    if (-not (Test-Path -LiteralPath $Path)) {
        throw "$Description was not found: $Path"
    }
}

function Invoke-PythonScript {
    param(
        [string]$ScriptPath,
        [string]$Description
    )

    Require-Path -Path $ScriptPath -Description $Description
    Write-Host "Running: $Description" -ForegroundColor Yellow
    & python $ScriptPath

    if ($LASTEXITCODE -ne 0) {
        throw "$Description failed with exit code $LASTEXITCODE."
    }
}

Write-Stage "FMCL-CETAS pilot-study reproduction workflow"
Write-Host "Repository root: $RepositoryRoot"

Require-Path -Path $RawDirectory -Description "Raw-data directory"
Require-Path -Path (Join-Path $RawDirectory "manifest.csv") -Description "Raw-data manifest"
Require-Path -Path (Join-Path $ScriptsDirectory "verify_raw_archive.ps1") -Description "Raw-archive verifier"
Require-Path -Path (Join-Path $ScriptsDirectory "rebuild_table3_temperature_summary.py") -Description "Table 3 rebuild script"
Require-Path -Path (Join-Path $ScriptsDirectory "make_figure4_data_coverage.py") -Description "Figure 4 rebuild script"
Require-Path -Path (Join-Path $ScriptsDirectory "audit_pilot_study_consistency.py") -Description "Consistency audit script"

Write-Stage "Checking Python"
$pythonVersion = & python --version 2>&1
if ($LASTEXITCODE -ne 0) {
    throw "Python was not found on PATH. Install Python 3.10+ and retry."
}
Write-Host $pythonVersion -ForegroundColor Green

$requirements = Join-Path $ScriptsDirectory "requirements.txt"
if ((-not $SkipPythonInstall) -and (Test-Path -LiteralPath $requirements)) {
    Write-Host "Installing/verifying Python dependencies from scripts\requirements.txt" -ForegroundColor Yellow
    & python -m pip install -r $requirements
    if ($LASTEXITCODE -ne 0) {
        throw "Python dependency installation failed with exit code $LASTEXITCODE."
    }
}
elseif ($SkipPythonInstall) {
    Write-Host "Skipping Python package installation by request." -ForegroundColor Yellow
}
else {
    Write-Warning "scripts\requirements.txt was not found; Python packages were not checked."
}

Write-Stage "Verifying raw telemetry archive"
& powershell.exe -NoProfile -ExecutionPolicy Bypass -File (Join-Path $ScriptsDirectory "verify_raw_archive.ps1") -RepositoryRoot $RepositoryRoot
if ($LASTEXITCODE -ne 0) {
    throw "Raw-archive verification failed with exit code $LASTEXITCODE."
}

Write-Stage "Rebuilding temperature summaries"
Invoke-PythonScript `
    -ScriptPath (Join-Path $ScriptsDirectory "rebuild_table3_temperature_summary.py") `
    -Description "Table 3 and device/run temperature audit rebuild"

Write-Stage "Rebuilding Figure 4"
Invoke-PythonScript `
    -ScriptPath (Join-Path $ScriptsDirectory "make_figure4_data_coverage.py") `
    -Description "Figure 4 telemetry-coverage rebuild"

Write-Stage "Running cross-file consistency audit"
Invoke-PythonScript `
    -ScriptPath (Join-Path $ScriptsDirectory "audit_pilot_study_consistency.py") `
    -Description "Pilot-study consistency audit"

if (-not $SkipChecksumManifest) {
    Write-Stage "Generating SHA-256 file manifest"
    $manifestOutput = Join-Path $ReproducibilityDirectory "file_manifest_sha256.csv"

    $entries = @(
        Get-ChildItem -LiteralPath $RepositoryRoot -Recurse -File |
        Where-Object {
            $_.FullName -ne $manifestOutput -and
            $_.FullName -notmatch "\\\.git\\"
        } |
        Sort-Object FullName |
        ForEach-Object {
            $relativePath = $_.FullName.Substring($RepositoryRoot.Length).TrimStart("\") -replace "\\", "/"
            $hash = (Get-FileHash -LiteralPath $_.FullName -Algorithm SHA256).Hash

            [PSCustomObject]@{
                relative_path = $relativePath
                size_bytes    = $_.Length
                sha256        = $hash
            }
        }
    )

    $entries | Export-Csv -LiteralPath $manifestOutput -NoTypeInformation -Encoding UTF8
    Write-Host "Wrote checksum manifest: $manifestOutput" -ForegroundColor Green
}
else {
    Write-Host "Skipping SHA-256 file-manifest generation by request." -ForegroundColor Yellow
}

Write-Stage "Workflow complete"
Write-Host "Reproduced/verified outputs:" -ForegroundColor Green
Write-Host "  data\processed\Table3_condition_level_summary.csv"
Write-Host "  data\processed\TableS10_device_run_temperature_audit.csv"
Write-Host "  results\tables\Table3_condition_level_temperature_summary.md"
Write-Host "  results\figures\Figure4_telemetry_coverage.pdf"
Write-Host "  results\figures\Figure4_telemetry_coverage.png"
Write-Host "  results\figures\Figure4_telemetry_coverage_values.csv"
if (-not $SkipChecksumManifest) {
    Write-Host "  reproducibility\file_manifest_sha256.csv"
}
