<#
Build one complete Windows setup EXE. Each release carries the app, Python,
COLMAP, and GLOMAP; recipients never extract a ZIP. Run from PowerShell with -RuntimeSource
pointing to a tested development runtime (.venv and tools) or an existing
installer-based PhotoMesh Studio installation (python, tools, app/runtime.id).
The build reads that source and writes only to StageDir/OutputDir.
#>
param(
    [Parameter(Mandatory=$true)][string]$RuntimeSource,
    [Parameter(Mandatory=$true)][string]$ISCC,
    [string]$OutputDir = (Join-Path $PSScriptRoot "..\dist"),
    [string]$StageDir = (Join-Path $PSScriptRoot "..\release-stage"),
    [string]$EngineCache = (Join-Path $env:LOCALAPPDATA "PhotoMeshStudioBuild\engine-cache"),
    [switch]$OfflineBuild,
    [switch]$CompactPayload = $true,
    [switch]$IncludeNeuralGPU,
    [switch]$BuildNeuralAddon = $true,
    [string]$Revision = ''
)
$ErrorActionPreference = "Stop"
$app = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot ".."))
$runtime = [IO.Path]::GetFullPath($RuntimeSource)
$stage = [IO.Path]::GetFullPath($StageDir)
$out = [IO.Path]::GetFullPath($OutputDir)
$compiler = [IO.Path]::GetFullPath($ISCC)
if (-not (Test-Path -LiteralPath $compiler -PathType Leaf)) { throw "ISCC.exe not found: $compiler" }
if (Test-Path -LiteralPath $stage) { throw "Stage already exists: $stage. Choose a fresh -StageDir." }
$venv = Join-Path $runtime "photomesh-studio\.venv"
$venvPy = Join-Path $venv "Scripts\python.exe"
$site = Join-Path $venv "Lib\site-packages"
$installedPython = Join-Path $runtime "python\python.exe"
$installedIdPath = Join-Path $runtime "app\runtime.id"
$colmap = Join-Path $runtime "tools\colmap"
$glomap = Join-Path $runtime "tools\glomap"
foreach ($p in @($colmap)) {
    if (-not (Test-Path -LiteralPath $p)) { throw "Required runtime path missing: $p" }
}
if ((Test-Path -LiteralPath $venvPy -PathType Leaf) -and (Test-Path -LiteralPath $site -PathType Container)) {
    $sourceMode = "venv"
    $cfg = Get-Content -LiteralPath (Join-Path $venv "pyvenv.cfg")
    $base = (($cfg | Where-Object { $_ -match "^home\s*=" } | Select-Object -First 1) -replace "^home\s*=\s*", "").Trim()
    if (-not (Test-Path -LiteralPath (Join-Path $base "pythonw.exe"))) { throw "Base Python missing: $base" }
} elseif ((Test-Path -LiteralPath $installedPython -PathType Leaf) -and (Test-Path -LiteralPath $installedIdPath -PathType Leaf)) {
    $sourceMode = "installed"
    $runtimeId = (Get-Content -LiteralPath $installedIdPath -Raw).Trim()
    if ($runtimeId -notmatch '^[0-9a-fA-F]{64}$') { throw "Invalid installed runtime ID: $installedIdPath" }
    Write-Host "Reusing installed runtime from $runtime"
} else {
    throw "RuntimeSource must contain photomesh-studio\.venv or an installed app with python\python.exe and app\runtime.id: $runtime"
}
$versionText = Get-Content -LiteralPath (Join-Path $app "photomesh\__init__.py") -Raw
if ($versionText -notmatch 'APP_VERSION\s*=\s*"([^"]+)"') { throw "APP_VERSION missing" }
$version = $Matches[1]
$installerName = "Lens2Mesh_Setup_$version.exe"
if (Test-Path -LiteralPath (Join-Path $out $installerName)) { throw "Output already exists: $installerName" }

function Copy-Tree([string]$Source, [string]$Destination, [string[]]$ExcludeDirs = @(), [string[]]$ExcludeFiles = @()) {
    New-Item -ItemType Directory -Force -Path $Destination | Out-Null
    $args = @($Source, $Destination, "/E", "/NFL", "/NDL", "/NJH", "/NJS", "/NP", "/R:1", "/W:1")
    if ($ExcludeDirs.Count) { $args += "/XD"; $args += $ExcludeDirs }
    if ($ExcludeFiles.Count) { $args += "/XF"; $args += $ExcludeFiles }
    & robocopy @args | Out-Null
    if ($LASTEXITCODE -ge 8) { throw "Copy failed ($LASTEXITCODE): $Source" }
    $global:LASTEXITCODE = 0
}

New-Item -ItemType Directory -Force -Path $stage, $out | Out-Null
Write-Host "Staging Lens2Mesh $version"
$appStage = Join-Path $stage "app"
Copy-Tree (Join-Path $app "photomesh") (Join-Path $appStage "photomesh") @("__pycache__", (Join-Path $app "photomesh\resources\neural-cuda12")) @("*.pyc", "*.log")
foreach ($name in @("main.py", "LICENSE", "README.md", "CHANGES.md", "UPDATING.md", "SCREENSHOT-LICENSE.txt", "requirements.txt", "run.bat", "setup.bat")) {
    Copy-Item -LiteralPath (Join-Path $app $name) -Destination (Join-Path $appStage $name)
}

# Keep local Help links and the README screenshot available in the installed app.
Copy-Tree (Join-Path $app "docs") (Join-Path $appStage "docs")
foreach ($screenshot in @("screenshot.png", "screenshot-light.png")) {
    Copy-Item -LiteralPath (Join-Path $app $screenshot) -Destination (Join-Path $appStage $screenshot)
}
New-Item -ItemType Directory -Force -Path (Join-Path $appStage "packaging") | Out-Null
foreach ($guide in @("README.md", "RELEASE.md", "fix_shortcut_icon.ps1", "migrate_shortcuts.ps1", "requirements-runtime-win313.lock")) {
    Copy-Item -LiteralPath (Join-Path $PSScriptRoot $guide) -Destination (Join-Path (Join-Path $appStage "packaging") $guide)
}

Write-Host "Copying Python and its tested packages"
$pythonStage = Join-Path $stage "python"
if ($sourceMode -eq "venv") {
    Copy-Tree $base $pythonStage @("site-packages", "__pycache__") @("*.pyc")
    Copy-Tree $site (Join-Path $pythonStage "Lib\site-packages") @("__pycache__") @("*.pyc")
} else {
    Copy-Tree (Join-Path $runtime "python") $pythonStage @("__pycache__") @("*.pyc")
}
Write-Host "Removing the independently replaced PLY dependency and reviewed unused Qt addons"
& (Join-Path $pythonStage "python.exe") (Join-Path $app "packaging\runtime_dependencies.py") --stage $stage
if ($LASTEXITCODE -ne 0) { throw "Staged dependency cleanup failed" }
Write-Host "Checking the exact audited Windows package versions"
& (Join-Path $pythonStage "python.exe") (Join-Path $app "packaging\verify_runtime_lock.py") --root $stage
if ($LASTEXITCODE -ne 0) { throw "Staged package versions differ from the audited lock" }
Write-Host "Retaining the tested legacy reconstruction engine"
$legacyColmap = Join-Path $runtime "tools\colmap-legacy"
if (-not (Test-Path -LiteralPath $legacyColmap)) { $legacyColmap = $colmap }
Copy-Tree $legacyColmap (Join-Path $stage "tools\colmap-legacy")
if (Test-Path -LiteralPath $glomap) { Copy-Tree $glomap (Join-Path $stage "tools\glomap") }
Write-Host "Preparing pinned COLMAP 4.2.1 CPU/CUDA engines and offline neural models"
$engineArgs = @((Join-Path $app "tools\prepare_engine.py"), "--output", (Join-Path $stage "tools"), "--cache", $EngineCache)
if ($OfflineBuild) { $engineArgs += "--offline" }
& (Join-Path $pythonStage "python.exe") @engineArgs
if ($LASTEXITCODE -ne 0) { throw "Offline engine bundle preparation failed" }
$neuralArgs = @((Join-Path $app "packaging\neural_runtime.py"), "--output", (Join-Path $appStage "photomesh\resources\neural-cuda12"), "--cache", $EngineCache)
if (-not $IncludeNeuralGPU) { $neuralArgs += '--descriptor-only' }
if ($OfflineBuild) { $neuralArgs += "--offline" }
& (Join-Path $pythonStage "python.exe") @neuralArgs
if ($LASTEXITCODE -ne 0) { throw "Verified neural CUDA runtime preparation failed" }
$neuralAddonRuntime = Join-Path $appStage 'photomesh/resources/neural-cuda12'
if ($BuildNeuralAddon -and -not $IncludeNeuralGPU) {
    $neuralAddonRuntime = $stage + '-neural-addon-runtime'
    $addonArgs = @((Join-Path $app 'packaging/neural_runtime.py'), '--output', $neuralAddonRuntime, '--cache', $EngineCache)
    if ($OfflineBuild) { $addonArgs += '--offline' }
    & (Join-Path $pythonStage 'python.exe') @addonArgs
    if ($LASTEXITCODE) { throw 'Optional GPU add-on runtime preparation failed' }
}

if ($sourceMode -eq "venv") {
    $freeze = @(& (Join-Path $pythonStage "python.exe") -m pip freeze --exclude-editable | Sort-Object)
    if ($LASTEXITCODE -ne 0) { throw "pip freeze failed" }
    $pyver = (& $venvPy -c "import sys; print(sys.version.split()[0])")
    $colhash = (Get-FileHash -LiteralPath (Join-Path $colmap "bin\colmap.exe") -Algorithm SHA256).Hash
    $glhash = "not bundled"
    if (Test-Path -LiteralPath (Join-Path $glomap "bin\glomap.exe")) { $glhash = (Get-FileHash -LiteralPath (Join-Path $glomap "bin\glomap.exe") -Algorithm SHA256).Hash }
    $runtimeDescription = @("python=$pyver", "colmap=$colhash", "glomap=$glhash") + $freeze
    $sha = [Security.Cryptography.SHA256]::Create()
    $runtimeId = ([BitConverter]::ToString($sha.ComputeHash([Text.Encoding]::UTF8.GetBytes(($runtimeDescription -join "`n")))) -replace "-", "").ToLowerInvariant()
    $sha.Dispose()
} else {
    $runtimeDescription = @("Reused installed runtime ID: $runtimeId")
}
$engineHash = (Get-FileHash -LiteralPath (Join-Path $stage "tools\colmap\photomesh-engine.json") -Algorithm SHA256).Hash.ToLowerInvariant()
$runtimeDescription += "runtime-cleanup=independent-ply-codec; removed-plyfile-and-reviewed-unused-Qt-addons"
$runtimeDescription += "modern-engine-manifest=$engineHash"
$neuralHash = (Get-FileHash -LiteralPath (Join-Path $appStage "photomesh\resources\neural-cuda12\runtime.json") -Algorithm SHA256).Hash.ToLowerInvariant()
$runtimeDescription += "neural-cuda12-manifest=$neuralHash"
if (-not $IncludeNeuralGPU) { $runtimeDescription += 'neural-gpu=optional-add-on' }
$sha = [Security.Cryptography.SHA256]::Create()
$runtimeId = ([BitConverter]::ToString($sha.ComputeHash([Text.Encoding]::UTF8.GetBytes(($runtimeDescription -join "`n")))) -replace "-", "").ToLowerInvariant()
$sha.Dispose()
Set-Content -LiteralPath (Join-Path $appStage "runtime.id") -Value $runtimeId -Encoding ascii
Set-Content -LiteralPath (Join-Path $stage "runtime.lock") -Value $runtimeDescription -Encoding utf8
Set-Content -LiteralPath (Join-Path $appStage "release_manifest.txt") -Value @("Lens2Mesh $version", "Runtime ID: $runtimeId") -Encoding utf8

Write-Host "Validating copied runtime"
$env:PYTHONDONTWRITEBYTECODE = "1"
$env:QT_QPA_PLATFORM = "offscreen"
$env:PYTHONPATH = $appStage
$env:PHOTOMESH_STAGE_APP = $appStage
& (Join-Path $pythonStage "python.exe") -c "import os, sys; sys.path.insert(0, os.environ['PHOTOMESH_STAGE_APP']); import PySide6, numpy, scipy, open3d, pyproj, psutil, photomesh; from pathlib import Path; assert Path(photomesh.__file__).resolve().is_relative_to(Path(os.environ['PHOTOMESH_STAGE_APP']).resolve()); from photomesh.memguard import require_available_bytes; print('Runtime OK:', photomesh.APP_VERSION, require_available_bytes())"
if ($LASTEXITCODE -ne 0) { throw "Copied Python runtime failed validation" }

Write-Host "Building full installer"
$iss = Join-Path $PSScriptRoot "release.iss"
$compilerArgs = @("/Q", "/DAppVersion=$version", "/DStageDir=$stage", "/DOutputDir=$out")
if ($CompactPayload) {
    $packedFiles = Join-Path $out 'installer-files.iss'
    $neuralProfile = if ($IncludeNeuralGPU) {'full'} else {'base'}
    & (Join-Path $pythonStage 'python.exe') (Join-Path $PSScriptRoot 'installer_payload.py') --stage $stage --output $packedFiles --report (Join-Path $out 'installer-payload.json') --neural-profile $neuralProfile
    if ($LASTEXITCODE -ne 0) { throw 'Compact installer payload validation failed' }
    $compilerArgs += "/DPackedFiles=$packedFiles"
}
& $compiler @compilerArgs $iss
if ($LASTEXITCODE -ne 0) { throw "Full installer compilation failed" }
$file = Join-Path $out $installerName
$hash = (Get-FileHash -LiteralPath $file -Algorithm SHA256).Hash.ToLowerInvariant()
"$hash *$installerName" | Set-Content -LiteralPath "$file.sha256" -Encoding ascii
Write-Host "$installerName  $((Get-Item -LiteralPath $file).Length) bytes  SHA256 $hash"
Write-Host "Release complete. Staging retained at $stage for verification."
if ($BuildNeuralAddon) {
    if (-not $Revision) { $Revision = (& git -C $app rev-parse HEAD).Trim() }
    & (Join-Path $PSScriptRoot 'build_neural_addon.ps1') -RuntimeFolder $neuralAddonRuntime -ISCC $compiler -OutputDir $out -Revision $Revision -Python (Join-Path $pythonStage 'python.exe')
    if ($LASTEXITCODE) { throw 'Optional GPU add-on installer build failed' }
}
