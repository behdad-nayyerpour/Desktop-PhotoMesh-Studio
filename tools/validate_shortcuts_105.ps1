param([Parameter(Mandatory=$true)][string]$Fixture)
$ErrorActionPreference = 'Stop'
$Fixture = [IO.Path]::GetFullPath($Fixture)
if (Test-Path -LiteralPath $Fixture) { throw 'Use a new disposable shortcut fixture' }
$App = Join-Path $Fixture 'custom install\app'
$Desktop = Join-Path $Fixture 'desktop'
$Other = Join-Path $Fixture 'other desktop'
$Collision = Join-Path $Fixture 'occupied desktop'
New-Item -ItemType Directory -Force -Path $App,$Desktop,$Other,$Collision,(Join-Path $App 'photomesh\resources') | Out-Null
Set-Content -LiteralPath (Join-Path $App 'photomesh\resources\photomesh.ico') -Value 'fixture'
$Python = Join-Path (Split-Path $App) 'python\pythonw.exe'
$Main = Join-Path $App 'main.py'
$Arguments = '"'+$Main+'" "project with spaces.pmsx"'
$Shell = New-Object -ComObject WScript.Shell
foreach ($Directory in @($Desktop,$Other,$Collision)) {
    $Link = $Shell.CreateShortcut((Join-Path $Directory 'PhotoMesh Studio.lnk'))
    $Link.TargetPath = $Python
    $Link.Arguments = $Arguments
    $Link.WorkingDirectory = $App
    if ($Directory -eq $Other) { $Link.TargetPath = 'C:\Windows\notepad.exe' }
    $Link.Save()
}
$Original = (Get-FileHash -LiteralPath (Join-Path $Desktop 'PhotoMesh Studio.lnk')).Hash
$Unrelated = (Get-FileHash -LiteralPath (Join-Path $Other 'PhotoMesh Studio.lnk')).Hash
Set-Content -LiteralPath (Join-Path $Collision 'Lens2Mesh.lnk') -Value 'unrelated occupied path'
$Occupied = (Get-FileHash -LiteralPath (Join-Path $Collision 'Lens2Mesh.lnk')).Hash
& (Join-Path $PSScriptRoot '..\packaging\migrate_shortcuts.ps1') -Repo $App -Directories @($Desktop,$Other,$Collision)
$New = Join-Path $Desktop 'Lens2Mesh.lnk'
if (-not (Test-Path -LiteralPath $New)) { throw 'Owned shortcut was not renamed' }
if (Test-Path -LiteralPath (Join-Path $Desktop 'PhotoMesh Studio.lnk')) { throw 'Legacy shortcut remains' }
if ((Get-FileHash -LiteralPath (Join-Path $Desktop 'PhotoMesh Studio.lnk.lens2mesh-backup')).Hash -ne $Original) { throw 'Original shortcut backup differs' }
$Link = $Shell.CreateShortcut($New)
if ($Link.TargetPath -ne $Python -or $Link.Arguments -ne $Arguments -or $Link.WorkingDirectory -ne $App) { throw 'Launcher parameters changed' }
if ($Link.IconLocation -ne ((Join-Path $App 'photomesh\resources\photomesh.ico')+',0')) { throw 'Icon location differs' }
if ((Get-FileHash -LiteralPath (Join-Path $Other 'PhotoMesh Studio.lnk')).Hash -ne $Unrelated) { throw 'Unrelated shortcut changed' }
if ((Get-FileHash -LiteralPath (Join-Path $Collision 'Lens2Mesh.lnk')).Hash -ne $Occupied) { throw 'Occupied shortcut changed' }
$Renamed = (Get-FileHash -LiteralPath $New).Hash
& (Join-Path $PSScriptRoot '..\packaging\migrate_shortcuts.ps1') -Repo $App -Directories @($Desktop,$Other,$Collision)
if ((Get-FileHash -LiteralPath $New).Hash -ne $Renamed) { throw 'Repeated migration changed shortcut' }
Write-Output 'Exact-install shortcut ownership, custom path, preserved arguments, backup, collision, unrelated shortcut and repeat validation passed.'
