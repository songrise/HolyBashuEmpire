[CmdletBinding()]
param(
    [string]$GameDirectory = 'D:\SteamLibrary\steamapps\common\Europa Universalis V',
    [string]$UserDataPath = (Join-Path ([Environment]::GetFolderPath('MyDocuments')) 'Paradox Interactive\EU5 Holy Bashu Empire'),
    [switch]$DebugMode
)
$ErrorActionPreference = 'Stop'
$modSource = Join-Path $PSScriptRoot 'mod\holy_bashu_empire'
if (-not (Test-Path -LiteralPath $modSource)) { $modSource = Join-Path $PSScriptRoot 'holy_bashu_empire' }
$modSource = [IO.Path]::GetFullPath($modSource)
$exePath = Join-Path $GameDirectory 'binaries\eu5.exe'
if (-not (Test-Path -LiteralPath $exePath)) { throw 'EU5 executable not found. Pass -GameDirectory with your installation path.' }
if (-not (Test-Path -LiteralPath (Join-Path $modSource '.metadata\metadata.json'))) { throw 'Mod metadata not found.' }
$dataArgument = '-userdir="' + [IO.Path]::GetFullPath($UserDataPath).Replace('\','/') + '"'
# The engine re-reads playsets when entering a game; -mod alone only mounts the frontend.
New-Item -ItemType Directory -Path $UserDataPath -Force | Out-Null
$playsetFile = Join-Path $UserDataPath 'playsets.json'
if (Test-Path -LiteralPath $playsetFile) {
    $playsetDoc = Get-Content -LiteralPath $playsetFile -Raw -Encoding UTF8 | ConvertFrom-Json
    Copy-Item -LiteralPath $playsetFile -Destination ($playsetFile + '.hbe-backup') -Force
} else { $playsetDoc = [pscustomobject]@{file_version='1.0.0';playsets=@()} }
$ownName = 'Holy Bashu Empire v0.01'
$retained = @($playsetDoc.playsets | Where-Object { $_.name -ne $ownName })
foreach ($existingPlayset in $retained) { $existingPlayset.isActive = $false }
$hbePlayset = [pscustomobject]@{ name=$ownName;isActive=$true;isAutomaticallySorted=$true;
    orderedListMods=@([pscustomobject]@{path=$modSource.Replace('\','/');isEnabled=$true});
    DLC=@([pscustomobject]@{paradoxAppId='d000_shared';isEnabled=$true}) }
$playsetDoc.playsets = @($retained) + @($hbePlayset)
[IO.File]::WriteAllText($playsetFile,($playsetDoc | ConvertTo-Json -Depth 10),[Text.UTF8Encoding]::new($false))
$launchArguments = @($dataArgument)
if ($DebugMode) { $launchArguments += '-debug_mode' }
# This script is explicitly used by the player to launch the interactive game.
Start-Process -FilePath $exePath -WorkingDirectory $GameDirectory -ArgumentList $launchArguments
