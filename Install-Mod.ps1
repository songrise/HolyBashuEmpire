[CmdletBinding()]
param(
    [string]$UserDataPath = (Join-Path ([Environment]::GetFolderPath('MyDocuments')) 'Paradox Interactive\Europa Universalis V'),
    [string]$ModDirectory = '',
    [string]$GamePath = '',
    [switch]$UpdatePlayset
)
$ErrorActionPreference = 'Stop'
$modSource = Join-Path $PSScriptRoot 'mod\holy_bashu_empire'
if (-not (Test-Path -LiteralPath $modSource)) { $modSource = Join-Path $PSScriptRoot 'holy_bashu_empire' }
if (-not (Test-Path -LiteralPath (Join-Path $modSource '.metadata\metadata.json'))) { throw 'Standalone mod folder was not found next to the installer.' }
# EU5 1.4.2 may fail opening non-ASCII mod paths. Use a native scan root,
# rather than assuming an arbitrary ASCII path in playsets.json is discoverable.
# User data and saves remain in place.
if (-not $ModDirectory) {
    $ModDirectory = Join-Path $UserDataPath 'mod'
    if ($ModDirectory -match '[^\x00-\x7F]') {
        if (-not $GamePath) {
            $steamRoot = (Get-ItemProperty -Path 'HKCU:\Software\Valve\Steam' -ErrorAction SilentlyContinue).SteamPath
            $libraries = @()
            if ($steamRoot) {
                $libraries += $steamRoot
                $libraryFile = Join-Path $steamRoot 'steamapps\libraryfolders.vdf'
                if (Test-Path -LiteralPath $libraryFile) {
                    $libraryText = Get-Content -LiteralPath $libraryFile -Raw
                    foreach ($match in [regex]::Matches($libraryText, '"path"\s+"([^"]+)"')) {
                        $libraries += $match.Groups[1].Value.Replace('\\','\')
                    }
                }
            }
            foreach ($library in $libraries) {
                $candidate = Join-Path $library 'steamapps\common\Europa Universalis V'
                if (Test-Path -LiteralPath (Join-Path $candidate 'binaries\eu5.exe')) { $GamePath = $candidate; break }
            }
        }
        if (-not $GamePath -or -not (Test-Path -LiteralPath (Join-Path $GamePath 'binaries\eu5.exe'))) {
            throw 'Non-ASCII user directory: specify -GamePath with the EU5 installation directory so the mod can use the native game/mod scan root.'
        }
        $ModDirectory = Join-Path $GamePath 'game\mod'
    }
}
if ($ModDirectory -match '[^\x00-\x7F]') { throw 'EU5 1.4.2 requires an ASCII mod path. Specify -ModDirectory with an ASCII directory.' }
$modParent = [IO.Path]::GetFullPath($ModDirectory)
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
$installedVersion = (Get-Content -LiteralPath (Join-Path $modTarget '.metadata\metadata.json') -Raw -Encoding UTF8 | ConvertFrom-Json).version
Write-Output "Installed Holy Bashu Empire v$installedVersion at $modTarget"
if ($UpdatePlayset) {
    $playsetPath = Join-Path $UserDataPath 'playsets.json'
    if (Test-Path -LiteralPath $playsetPath) {
        $playsets = Get-Content -LiteralPath $playsetPath -Raw -Encoding UTF8 | ConvertFrom-Json
        $oldDefault = [IO.Path]::GetFullPath((Join-Path $UserDataPath 'mod\holy_bashu_empire')).Replace('\','/').TrimEnd('/')
        $newPath = $modTarget.Replace('\','/').TrimEnd('/')
        $oldAscii = ([IO.Path]::GetFullPath((Join-Path ([Environment]::GetFolderPath('LocalApplicationData')) 'HolyBashuEmpire\mod\holy_bashu_empire'))).Replace('\','/').TrimEnd('/')
        $updated = 0
        foreach ($playset in $playsets.playsets) {
            foreach ($entry in $playset.orderedListMods) {
                $entryPath = ([string]$entry.path).Replace('\','/').TrimEnd('/')
                if ($entryPath -eq $oldDefault -or $entryPath -eq $oldAscii -or $entryPath -eq $newPath) {
                    $entry.path = $newPath + '/'
                    $updated++
                }
            }
        }
        if ($updated -gt 0) {
            $backupParent = [IO.Path]::GetFullPath((Join-Path $UserDataPath 'hbe-mod-backups'))
            New-Item -ItemType Directory -Path $backupParent -Force | Out-Null
            $playsetBackup = Join-Path $backupParent ('playsets.' + (Get-Date -Format 'yyyyMMddHHmmssfff') + '.json')
            Copy-Item -LiteralPath $playsetPath -Destination $playsetBackup
            [IO.File]::WriteAllText($playsetPath,($playsets | ConvertTo-Json -Depth 30),[Text.UTF8Encoding]::new($false))
            Write-Output "Updated $updated existing HBE playset reference(s); backup: $playsetBackup"
        }
    }
}
Write-Output 'Enable the mod in the EU5 mod manager, then start a NEW 1337 game.'
