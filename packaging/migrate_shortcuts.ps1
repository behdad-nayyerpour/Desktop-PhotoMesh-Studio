<# Rename only legacy shortcuts that launch this exact installation.
   Keep a byte-for-byte backup and never overwrite another shortcut.
   -Directories is used by disposable integration fixtures, not the app.
#>
param(
    [Parameter(Mandatory=$true)][string]$Repo,
    [string[]]$Directories
)
$ErrorActionPreference = 'Stop'
$Repo = (Resolve-Path -LiteralPath $Repo).Path.TrimEnd('\','/')
$Install = Split-Path -Parent $Repo
$Icon = Join-Path $Repo 'photomesh\resources\photomesh.ico'
if (-not (Test-Path -LiteralPath $Icon -PathType Leaf)) { exit 1 }
$ExpectedPython = Join-Path $Install 'python\pythonw.exe'
$ExpectedMain = Join-Path $Repo 'main.py'
$Shell = New-Object -ComObject WScript.Shell
if (-not $Directories) {
    $Directories = @([Environment]::GetFolderPath('Desktop'), [Environment]::GetFolderPath('Programs'))
}
foreach ($Directory in $Directories) {
    if (-not $Directory -or -not (Test-Path -LiteralPath $Directory -PathType Container)) { continue }
    $Directory = (Resolve-Path -LiteralPath $Directory).Path
    $Old = Join-Path $Directory 'PhotoMesh Studio.lnk'
    $New = Join-Path $Directory 'Lens2Mesh.lnk'
    $Backup = Join-Path $Directory 'PhotoMesh Studio.lnk.lens2mesh-backup'
    if (-not (Test-Path -LiteralPath $Old -PathType Leaf) -or (Test-Path -LiteralPath $New)) { continue }
    try {
        if ((Get-Item -LiteralPath $Old).Attributes -band [IO.FileAttributes]::ReparsePoint) { continue }
        $Link = $Shell.CreateShortcut($Old)
        $Arguments = $Link.Arguments.Trim()
        $StartsMain = ($Arguments -eq ('"'+$ExpectedMain+'"')) -or ($Arguments -eq $ExpectedMain) -or
                      $Arguments.StartsWith(('"'+$ExpectedMain+'" '), [StringComparison]::OrdinalIgnoreCase)
        if ($Link.TargetPath -ne $ExpectedPython -or -not $StartsMain -or $Link.WorkingDirectory -ne $Repo) { continue }
        if (Test-Path -LiteralPath $Backup) { continue }
        Copy-Item -LiteralPath $Old -Destination $Backup -ErrorAction Stop
        $Link.IconLocation = "$Icon,0"
        $Link.Save()
        Move-Item -LiteralPath $Old -Destination $New -ErrorAction Stop
        Write-Output "Renamed shortcut: $New; original retained at $Backup"
    } catch {
        # Restore the original if updating/saving/renaming failed. The new path
        # is never overwritten; only a shortcut we just backed up is restored.
        if ((Test-Path -LiteralPath $Backup) -and (Test-Path -LiteralPath $Old)) {
            Copy-Item -LiteralPath $Backup -Destination $Old -Force
        }
        Write-Warning "Could not migrate shortcut in $Directory : $($_.Exception.Message)"
    }
}
