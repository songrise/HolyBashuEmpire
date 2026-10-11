[CmdletBinding()]
param(
    [string]$UserDataPath = (Join-Path ([Environment]::GetFolderPath('MyDocuments')) 'Paradox Interactive\Europa Universalis V')
)
$ErrorActionPreference = 'Stop'
$modSource = Join-Path $PSScriptRoot 'mod\holy_bashu_empire'
if (-not (Test-Path -LiteralPath $modSource)) { $modSource = Join-Path $PSScriptRoot 'holy_bashu_empire' }
if (-not (Test-Path -LiteralPath (Join-Path $modSource '.metadata\metadata.json'))) { throw 'Standalone mod folder was not found next to the installer.' }
$modParent = [IO.Path]::GetFullPath((Join-Path $UserDataPath 'mod'))
$modTarget = [IO.Path]::GetFullPath((Join-Path $modParent 'holy_bashu_empire'))
if (-not $modTarget.StartsWith($modParent + [IO.Path]::DirectorySeparatorChar,[StringComparison]::OrdinalIgnoreCase)) { throw 'Unsafe target path.' }
if (Test-Path -LiteralPath $modTarget) {
    $oldMetadata = Join-Path $modTarget '.metadata\metadata.json'
    if (-not (Test-Path -LiteralPath $oldMetadata)) { throw 'Target already exists and does not identify this mod. No files were changed.' }
    $oldName = (Get-Content -LiteralPath $oldMetadata -Raw -Encoding UTF8 | ConvertFrom-Json).name
    if ($oldName -notlike '*Holy Bashu Empire*') { throw 'Target belongs to a different mod. No files were changed.' }
    $backupParent = [IO.Path]::GetFullPath((Join-Path $UserDataPath 'hbe-mod-backups'))
    $modBackup = [IO.Path]::GetFullPath((Join-Path $backupParent ('holy_bashu_empire.' + (Get-Date -Format 'yyyyMMddHHmmssfff'))))
    if (-not $modBackup.StartsWith($backupParent + [IO.Path]::DirectorySeparatorChar,[StringComparison]::OrdinalIgnoreCase)) { throw 'Unsafe backup path.' }
    New-Item -ItemType Directory -Path $backupParent -Force | Out-Null
    Move-Item -LiteralPath $modTarget -Destination $modBackup
    Write-Output "Previous installation preserved at $modBackup"
}
New-Item -ItemType Directory -Path $modParent -Force | Out-Null
Copy-Item -LiteralPath $modSource -Destination $modParent -Recurse
Write-Output "Installed Holy Bashu Empire v0.01 at $modTarget"
Write-Output 'Enable the mod in the EU5 mod manager, then start a NEW 1337 game.'
