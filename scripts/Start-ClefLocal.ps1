[CmdletBinding()]
param(
    [string]$StorageRoot = (Split-Path -Parent $PSScriptRoot),
    [ValidateSet('cpu', 'vulkan')][string]$Backend = 'cpu',
    [ValidateRange(0, 999)][int]$GpuLayers = 0,
    [ValidateRange(1, 65535)][int]$Port = 30000,
    [ValidateRange(1, 256)][int]$Threads = 6
)

$ErrorActionPreference = 'Stop'
$project = . (Join-Path $PSScriptRoot 'Set-ProjectEnvironment.ps1') -StorageRoot $StorageRoot
. (Join-Path $PSScriptRoot 'ClefAssets.ps1')
if ($Backend -eq 'cpu' -and $GpuLayers -ne 0) { throw 'CPU backend requires -GpuLayers 0. Use -Backend vulkan for an existing compatible GPU.' }
$runtime = Get-ClefRuntimeAsset $Backend
$directory = Join-Path $project.RuntimeRoot $runtime.Directory
$archive = Join-Path $project.DownloadDirectory $runtime.File
Assert-DPath $directory
Assert-DPath $archive
Assert-DPath $project.ModelPath
$server = Assert-ClefRuntime $archive $directory $Backend
Assert-ClefFile $project.ModelPath $ClefAsset.ModelBytes $ClefAsset.ModelSha256

# Clef needs the whole prompt in a microbatch. 128 is unsuitable here.
$arguments = @(
    '--host', '127.0.0.1', '--port', "$Port",
    '-m', $project.ModelPath, '--alias', 'Cloudflare/clef-flash',
    '--ctx-size', '2048', '--batch-size', '2048', '--ubatch-size', '2048',
    '--parallel', '1', '--threads', "$Threads", '--n-gpu-layers', "$GpuLayers"
)
Write-Host "Starting verified local $Backend server on http://127.0.0.1:$Port (Ctrl+C to stop)."
Write-Host 'Model: Clef-Flash Q4_K_M; this uses real model probabilities, with no demo fallback.'
Push-Location -LiteralPath $project.StorageRoot
try {
    & $server @arguments
    if ($LASTEXITCODE -ne 0) { throw "Local llama-server exited with code $LASTEXITCODE. Check its diagnostics; no fallback was used." }
}
finally { Pop-Location }
