[CmdletBinding()]
param(
    [string]$StorageRoot = (Split-Path -Parent $PSScriptRoot),
    [ValidateSet('cpu', 'vulkan')][string]$Backend = 'cpu'
)

$ErrorActionPreference = 'Stop'
$project = . (Join-Path $PSScriptRoot 'Set-ProjectEnvironment.ps1') -StorageRoot $StorageRoot
. (Join-Path $PSScriptRoot 'ClefAssets.ps1')

function Get-PinnedDownload([string]$Url, [string]$Destination, [long]$Bytes, [string]$Sha256) {
    Assert-DPath $Destination
    Assert-DPath "$Destination.part"
    if (Test-Path -LiteralPath $Destination) {
        Assert-ClefFile $Destination $Bytes $Sha256
        Write-Host "Verified existing asset: $Destination"
        return
    }
    $partial = "$Destination.part"
    if ((Test-Path -LiteralPath $partial -PathType Leaf) -and (Get-Item -LiteralPath $partial).Length -eq $Bytes) {
        Assert-ClefFile $partial $Bytes $Sha256
        Move-Item -LiteralPath $partial -Destination $Destination
        Write-Host "Verified completed partial download: $Destination"
        return
    }
    Write-Host "Downloading pinned asset to D: $Destination"
    & curl.exe --fail --location --proto '=https' --proto-redir '=https' --retry 3 --retry-delay 2 --continue-at - --output $partial $Url
    $downloadExit = $LASTEXITCODE
    # Some servers reject range continuation. A fresh request is then explicit.
    if ($downloadExit -in @(33, 36)) {
        & curl.exe --fail --location --proto '=https' --proto-redir '=https' --retry 3 --retry-delay 2 --output $partial $Url
        $downloadExit = $LASTEXITCODE
    }
    if ($downloadExit -ne 0) { throw "Download failed (curl exit $downloadExit). The D: .part file is retained for resumption." }
    Assert-ClefFile $partial $Bytes $Sha256
    Move-Item -LiteralPath $partial -Destination $Destination
    Write-Host "Verified SHA-256: $Destination"
}

if (-not (Get-Command curl.exe -ErrorAction SilentlyContinue)) { throw 'An existing Windows curl.exe is required; no software will be installed globally.' }
$runtime = Get-ClefRuntimeAsset $Backend
$directory = Join-Path $project.RuntimeRoot $runtime.Directory
Assert-DPath $directory
$archive = Join-Path $project.DownloadDirectory $runtime.File
Get-PinnedDownload $runtime.Url $archive $runtime.Bytes $runtime.Sha256
Get-PinnedDownload $ClefAsset.ModelUrl $project.ModelPath $ClefAsset.ModelBytes $ClefAsset.ModelSha256

if (-not (Test-Path -LiteralPath $directory)) {
    # Extraction and any temporary files remain on D:. Never execute from .part.
    Expand-Archive -LiteralPath $archive -DestinationPath $directory
}
$server = Assert-ClefRuntime $archive $directory $Backend
Write-Host "Setup verified. Server: $server"
Write-Host 'No server has been started. Use Start-ClefLocal.ps1 for local inference.'
