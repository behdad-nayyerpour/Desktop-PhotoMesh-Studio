<# Build the optional, rollback-enabled NVIDIA runtime installer from exact DLLs. #>
param(
    [Parameter(Mandatory=$true)][string]$RuntimeFolder,
    [Parameter(Mandatory=$true)][string]$ISCC,
    [Parameter(Mandatory=$true)][string]$OutputDir,
    [Parameter(Mandatory=$true)][string]$Revision,
    [Parameter(Mandatory=$true)][string]$Python
)
$ErrorActionPreference='Stop'
$source=Split-Path -Parent $PSScriptRoot
$runtime=(Resolve-Path -LiteralPath $RuntimeFolder).Path
$out=[IO.Path]::GetFullPath($OutputDir)
$addon=Join-Path $out 'neural-addon-stage'
if (Test-Path -LiteralPath $addon) { throw 'Choose a fresh output directory for the GPU add-on' }
if ($Revision -notmatch '^[0-9a-f]{40}$') { throw 'An exact source revision is required' }
New-Item -ItemType Directory -Force (Join-Path $addon 'packaging') | Out-Null
# Source DLLs remain in their authenticated stage; the installer uses absolute sources.
& $Python (Join-Path $PSScriptRoot 'prepare_neural_addon.py') --runtime $runtime --output $addon
if ($LASTEXITCODE) { throw 'GPU add-on payload authentication failed' }
foreach ($name in @('neural_addon.py','apply_patch.py','neural-runtime-assets.json')) {
    Copy-Item -LiteralPath (Join-Path $PSScriptRoot $name) -Destination (Join-Path $addon 'packaging')
}
& $ISCC '/Q' "/DAddonStage=$addon" "/DRuntimeFolder=$runtime" "/DOutputDir=$out" "/DAddonRevision=$Revision" (Join-Path $PSScriptRoot 'neural-addon.iss')
if ($LASTEXITCODE) { throw 'GPU add-on Setup compilation failed' }
$file=Join-Path $out 'Lens2Mesh_NeuralGPU_Addon_1.0.5.exe'
$hash=(Get-FileHash -LiteralPath $file).Hash.ToLowerInvariant()
"$hash *Lens2Mesh_NeuralGPU_Addon_1.0.5.exe" | Set-Content "$file.sha256" -Encoding ascii
Write-Host "GPU add-on: $((Get-Item $file).Length) bytes; SHA256 $hash"
