param([switch]$Test, [switch]$Setup, [switch]$Check, [switch]$Offline, [switch]$DebugBuild, [switch]$LocalPbjb, [switch]$ExternalPbjb, [string]$Python = 'auto')
$ErrorActionPreference = 'Stop'
$root = $PSScriptRoot
$keys = @('TEMP','TMP','TMPDIR','PYTHONDONTWRITEBYTECODE','PIP_CACHE_DIR','PIP_CONFIG_FILE')
$saved = @{}
$exitCode = 0
$bootstrapLog = $null
foreach ($key in $keys) { $saved[$key] = [Environment]::GetEnvironmentVariable($key, 'Process') }
Push-Location -LiteralPath $root
try {
    . (Join-Path $root 'scripts/bootstrap-python.ps1')
    Write-Host 'PocketBook OPDS Patch - automatic local build'
    $tmp = Assert-ProjectPath $root (Join-Path $root '.cache/tmp')
    New-Item -ItemType Directory -Force -Path $tmp | Out-Null
    $bootstrapLog = Assert-ProjectPath $root (Join-Path $root '.cache/bootstrap.log')
    $env:TEMP = $tmp; $env:TMP = $tmp; $env:TMPDIR = $tmp
    $env:PYTHONDONTWRITEBYTECODE = '1'
    $env:PIP_CACHE_DIR = Join-Path $root '.cache/pip'
    $env:PIP_CONFIG_FILE = 'NUL'
    $pythonExecutable = Get-ProjectPython -Root $root -Requested $Python -NoDownload:($Check -or $Offline)
    $arguments = @('-I', '-B', 'scripts/build.py')
    if ($Test) { $arguments += '--test' }
    if ($Setup) { $arguments += '--setup' }
    if ($Check) { $arguments += '--check' }
    if ($Offline) { $arguments += '--offline' }
    if ($DebugBuild) { $arguments += '--debug' }
    if ($LocalPbjb) { $arguments += '--local-pbjb' }
    if ($ExternalPbjb) { $arguments += '--external-pbjb' }
    & $pythonExecutable @arguments
    $exitCode = $LASTEXITCODE
} catch {
    Write-Host ("[ERROR] " + $_.Exception.Message) -ForegroundColor Red
    if ($bootstrapLog) {
        try { Add-Content -LiteralPath $bootstrapLog -Encoding UTF8 -Value ((Get-Date -Format o) + ' ' + $_.Exception.ToString()) } catch {}
        Write-Host ('[INFO] Bootstrap log: ' + $bootstrapLog)
    }
    $exitCode = 2
} finally {
    Pop-Location
    foreach ($key in $keys) { [Environment]::SetEnvironmentVariable($key, $saved[$key], 'Process') }
}
exit $exitCode
