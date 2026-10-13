param(
    [int]$Port = 8765,
    [string]$ModPath = '',
    [switch]$NoBrowser
)
$ErrorActionPreference = 'Stop'
$viewerRoot = $PSScriptRoot
$pythonCandidates = @(
    (Join-Path $env:USERPROFILE '.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe'),
    (Get-Command python -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Source -First 1)
)
$viewerPython = $pythonCandidates | Where-Object { $_ -and (Test-Path -LiteralPath $_) } | Select-Object -First 1
if (-not $viewerPython) { throw 'Python 3.10+ is required.' }
$viewerUrl = "http://127.0.0.1:$Port"
$viewerReady = $false
try {
    $probe = Invoke-RestMethod "$viewerUrl/api/health" -TimeoutSec 2
    $viewerReady = [bool]$probe.stats.events
} catch {}
if (-not $viewerReady) {
    $runtimePath = Join-Path $viewerRoot '.runtime'
    New-Item -ItemType Directory -Path $runtimePath -Force | Out-Null
    $arguments = '"{0}" --port {1}' -f (Join-Path $viewerRoot 'server.py'), $Port
    if ($ModPath) { $arguments += ' --mod-path "{0}"' -f $ModPath }
    $viewerProcess = Start-Process -FilePath $viewerPython -ArgumentList $arguments -WorkingDirectory $viewerRoot -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $runtimePath 'server.log') -RedirectStandardError (Join-Path $runtimePath 'server-error.log')
    $viewerProcess.Id | Set-Content -LiteralPath (Join-Path $runtimePath 'server.pid')
    for ($attempt = 0; $attempt -lt 25; $attempt++) {
        Start-Sleep -Milliseconds 200
        try {
            $probe = Invoke-RestMethod "$viewerUrl/api/health" -TimeoutSec 1
            if ($probe.stats.events) { $viewerReady = $true; break }
        } catch {}
        if ($viewerProcess.HasExited) { break }
    }
    if (-not $viewerReady) {
        throw "Could not start event viewer. See $runtimePath/server-error.log"
    }
}
Write-Host "$viewerUrl  ($($probe.stats.events) events, $($probe.stats.options) options)"
if (-not $NoBrowser) { Start-Process $viewerUrl }
