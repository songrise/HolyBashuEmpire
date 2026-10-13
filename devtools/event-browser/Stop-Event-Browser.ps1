$ErrorActionPreference = 'Stop'
$pidPath = Join-Path $PSScriptRoot '.runtime/server.pid'
if (Test-Path -LiteralPath $pidPath) {
    $viewerPid = [int](Get-Content -LiteralPath $pidPath)
    $viewerProcess = Get-CimInstance Win32_Process -Filter "ProcessId = $viewerPid" -ErrorAction SilentlyContinue
    $expectedServer = Join-Path $PSScriptRoot 'server.py'
    if ($viewerProcess -and $viewerProcess.CommandLine -and $viewerProcess.CommandLine.Contains($expectedServer)) {
        Stop-Process -Id $viewerPid
        Write-Host 'Event viewer stopped.'
    } elseif ($viewerProcess) {
        throw 'PID is now used by another process; no process was stopped.'
    }
}
