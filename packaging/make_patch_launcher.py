"""Generate a standalone BAT pinned to a published candidate archive hash."""
import argparse
import base64
import re
from pathlib import Path


def create(url, sha256, output):
    if not re.fullmatch(r"https://raw\.githubusercontent\.com/[\w-]+/[\w.-]+/[0-9a-f]{40}/[\w./-]+\.zip", url):
        raise ValueError("Use a raw GitHub URL bound to an exact artifact commit")
    if not re.fullmatch("[0-9a-f]{64}", sha256):
        raise ValueError("Invalid archive checksum")
    code = r'''
$ErrorActionPreference='Stop'
try {
  $root=$env:LM_PATCH_ROOT
  if (-not $root) {
    $key='HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\{74DCCB58-21F5-4BB0-B93D-7DF3C76D64F5}_is1'
    $root=(Get-ItemProperty -LiteralPath $key -ErrorAction SilentlyContinue).InstallLocation
  }
  if (-not $root) { $root=Read-Host 'Installation folder containing app and python' }
  $root=[IO.Path]::GetFullPath($root)
  $py=Join-Path $root 'python\python.exe'
  if (-not (Test-Path -LiteralPath $py -PathType Leaf)) { throw 'Installed Python not found; choose the installation root' }
  $temp=Join-Path ([IO.Path]::GetTempPath()) ('Lens2Mesh-patch-'+[Guid]::NewGuid().ToString('N'))
  New-Item -ItemType Directory -Path $temp | Out-Null
  $zip=Join-Path $temp 'candidate.zip'
  Write-Host 'Downloading only the changed components. Close the application before continuing.'
  [Net.ServicePointManager]::SecurityProtocol=[Net.SecurityProtocolType]::Tls12
  Invoke-WebRequest -Uri '__URL__' -OutFile $zip -UseBasicParsing
  if ((Get-FileHash -LiteralPath $zip -Algorithm SHA256).Hash.ToLowerInvariant() -ne '__SHA__') { throw 'Download checksum mismatch; no application files changed' }
  $payload=Join-Path $temp 'payload'
  Expand-Archive -LiteralPath $zip -DestinationPath $payload
  & $py (Join-Path $payload 'apply_patch.py') --root $root --payload $payload
  if ($LASTEXITCODE) { throw 'Update failed; review the message above' }
  exit 0
} catch { Write-Host $_ -ForegroundColor Red; exit 1 }
'''.replace("__URL__", url).replace("__SHA__", sha256)
    encoded = base64.b64encode(code.encode("utf-16le")).decode("ascii")
    command = "powershell.exe -NoProfile -ExecutionPolicy Bypass -EncodedCommand " + encoded
    if len(command) >= 8000:
        raise ValueError("Bootstrap exceeds Windows command-line limit")
    bat = ('@echo off\r\nset "LM_PATCH_ROOT=%~1"\r\n' + command +
           '\r\nset "LM_PATCH_EXIT=%ERRORLEVEL%"\r\npause\r\nexit /b %LM_PATCH_EXIT%\r\n')
    output.write_bytes(bat.encode("ascii"))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", required=True)
    parser.add_argument("--sha256", required=True)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    create(args.url, args.sha256, args.output)
