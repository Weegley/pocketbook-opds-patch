# Project-local portable Python bootstrap. No registry/PATH/global installation.
function Assert-ProjectPath {
    param([string]$Root, [string]$Path)
    $base = [IO.Path]::GetFullPath($Root).TrimEnd('\', '/')
    $full = [IO.Path]::GetFullPath($Path)
    if (-not $full.StartsWith($base + [IO.Path]::DirectorySeparatorChar, [StringComparison]::OrdinalIgnoreCase)) {
        throw "Path must stay inside the project: $full"
    }
    $relative = $full.Substring($base.Length + 1)
    $current = $base
    foreach ($part in $relative.Split([char[]]@('\', '/'), [StringSplitOptions]::RemoveEmptyEntries)) {
        $current = Join-Path $current $part
        if (Test-Path -LiteralPath $current) {
            if ((Get-Item -LiteralPath $current -Force).Attributes -band [IO.FileAttributes]::ReparsePoint) {
                throw "Refusing a redirected project path: $current"
            }
        }
    }
    return $full
}

function Read-PythonBootstrapLock {
    param([string]$Root)
    $pins = @{}
    foreach ($line in Get-Content -LiteralPath (Join-Path $Root 'scripts/python-bootstrap.lock')) {
        if ($line -match '^([A-Z0-9_]+)=(.+)$') { $pins[$matches[1]] = $matches[2] }
    }
    foreach ($key in @('VERSION','WINDOWS_URL','WINDOWS_ARCHIVE','WINDOWS_SHA256','WINDOWS_INSTALL','WINDOWS_EXE')) {
        if (-not $pins.ContainsKey($key)) { throw "Missing bootstrap pin: $key" }
    }
    if ($pins.WINDOWS_SHA256 -notmatch '^[0-9a-f]{64}$') { throw 'Invalid Python SHA-256 pin' }
    return $pins
}

function Test-BuildPython {
    param([string]$Executable, [string]$ExactVersion = '')
    try {
        $output = & $Executable -I -B -c 'import sys,ssl,hashlib,zipfile; print(sys.version.split()[0]); sys.exit(0 if sys.version_info >= (3,11) else 2)' 2>&1
        if ($LASTEXITCODE -ne 0) { return $false }
        if ($ExactVersion -and (($output | Out-String).Trim() -ne $ExactVersion)) { return $false }
        return $true
    } catch { return $false }
}

function Get-ProjectPython {
    param([string]$Root, [string]$Requested = 'auto', [switch]$NoDownload)
    if ($Requested -and $Requested -ne 'auto') {
        $command = Get-Command $Requested -ErrorAction SilentlyContinue
        if (-not $command -or -not (Test-BuildPython $Requested)) {
            throw "Explicit Python override cannot run Python 3.11+ with SSL: $Requested. Omit -Python for automatic local bootstrap."
        }
        return $Requested
    }
    $pins = Read-PythonBootstrapLock $Root
    $runtime = Assert-ProjectPath $Root (Join-Path $Root ('.tools/python-runtime/' + $pins.WINDOWS_INSTALL))
    $executable = Join-Path $runtime $pins.WINDOWS_EXE
    if (Test-Path -LiteralPath $runtime) {
        if (-not (Test-BuildPython $executable $pins.VERSION)) {
            throw "Local Python is incomplete or damaged: $runtime. Inspect this cache before retrying; it will not be silently overwritten."
        }
        Write-Host ('[OK] Local Python ' + $pins.VERSION + ': ' + $executable)
        return $executable
    }
    if ($NoDownload) {
        throw ('Local Python ' + $pins.VERSION + ' is missing. Check/offline mode does not download. Run build.ps1 without -Check/-Offline to prepare everything automatically.')
    }
    $architecture = if ($env:PROCESSOR_ARCHITEW6432) { $env:PROCESSOR_ARCHITEW6432 } else { $env:PROCESSOR_ARCHITECTURE }
    if ($architecture -ne 'AMD64') { throw 'Automatic Windows bootstrap supports x86-64 only.' }
    $downloads = Assert-ProjectPath $Root (Join-Path $Root '.tools/downloads')
    $parent = Assert-ProjectPath $Root (Join-Path $Root '.tools/python-runtime')
    New-Item -ItemType Directory -Force -Path $downloads, $parent | Out-Null
    $archive = Assert-ProjectPath $Root (Join-Path $downloads $pins.WINDOWS_ARCHIVE)
    if (-not (Test-Path -LiteralPath $archive)) {
        $partial = Assert-ProjectPath $Root ($archive + '.part')
        Write-Host ('[DOWNLOAD] Portable Python ' + $pins.VERSION + ' -> .tools/downloads/')
        $previousProtocol = [Net.ServicePointManager]::SecurityProtocol
        try {
            [Net.ServicePointManager]::SecurityProtocol = $previousProtocol -bor [Net.SecurityProtocolType]::Tls12
            try {
                Invoke-WebRequest -UseBasicParsing -Uri $pins.WINDOWS_URL -OutFile $partial -TimeoutSec 180
            } catch {
                throw ('Python download failed: ' + $_.Exception.Message + '. Check network/proxy/certificates, or cache the pinned archive at ' + $archive)
            }
            if ((Get-FileHash -LiteralPath $partial -Algorithm SHA256).Hash.ToLowerInvariant() -ne $pins.WINDOWS_SHA256) {
                throw 'Portable Python download SHA-256 mismatch; nothing will be extracted.'
            }
            Move-Item -LiteralPath $partial -Destination $archive
        } finally { [Net.ServicePointManager]::SecurityProtocol = $previousProtocol }
    }
    if ((Get-FileHash -LiteralPath $archive -Algorithm SHA256).Hash.ToLowerInvariant() -ne $pins.WINDOWS_SHA256) {
        throw "Python archive SHA-256 mismatch: $archive. The cache is not overwritten automatically."
    }
    $stage = Assert-ProjectPath $Root (Join-Path $parent ('.install-' + [Guid]::NewGuid().ToString('N')))
    New-Item -ItemType Directory -Path $stage | Out-Null
    try {
        Write-Host '[SETUP] Extracting verified Python inside .tools/python-runtime/'
        Add-Type -AssemblyName System.IO.Compression.FileSystem
        $zip = [IO.Compression.ZipFile]::OpenRead($archive)
        try {
            foreach ($entry in $zip.Entries) {
                $entryPath = [IO.Path]::GetFullPath((Join-Path $stage $entry.FullName))
                if (-not $entryPath.StartsWith($stage + [IO.Path]::DirectorySeparatorChar, [StringComparison]::OrdinalIgnoreCase)) {
                    throw 'Unsafe Python ZIP path'
                }
                if ((($entry.ExternalAttributes -shr 16) -band 0xF000) -eq 0xA000) {
                    throw 'Unexpected Python ZIP symlink'
                }
            }
        } finally { $zip.Dispose() }
        [IO.Compression.ZipFile]::ExtractToDirectory($archive, $stage)
        if (-not (Test-BuildPython (Join-Path $stage $pins.WINDOWS_EXE) $pins.VERSION)) {
            throw 'Extracted Python failed its version/SSL check; it will not be activated.'
        }
        Move-Item -LiteralPath $stage -Destination $runtime
    } finally {
        if (Test-Path -LiteralPath $stage) {
            $safeStage = Assert-ProjectPath $Root $stage
            if (-not $safeStage.StartsWith($parent + [IO.Path]::DirectorySeparatorChar, [StringComparison]::OrdinalIgnoreCase)) {
                throw 'Refusing cleanup outside Python staging parent'
            }
            Remove-Item -LiteralPath $safeStage -Recurse -Force
        }
    }
    return $executable
}
