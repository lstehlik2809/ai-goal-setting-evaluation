# Shared immutable asset identity and integrity checks. This file does no I/O
# except when a verification function is explicitly called by setup/start.
$ClefAsset = @{
    RuntimeUrl = 'https://github.com/ggml-org/llama.cpp/releases/download/b11669/llama-b11669-bin-win-cpu-x64.zip'
    RuntimeFile = 'llama-b11669-bin-win-cpu-x64.zip'
    RuntimeBytes = 19537886L
    RuntimeSha256 = '37b3efcf962847ca869745fd4ccf7f5e7e8dacfeff9fa3523b4ca8cdc66d632b'
    VulkanUrl = 'https://github.com/ggml-org/llama.cpp/releases/download/b11669/llama-b11669-bin-win-vulkan-x64.zip'
    VulkanFile = 'llama-b11669-bin-win-vulkan-x64.zip'
    VulkanBytes = 32182350L
    VulkanSha256 = '2c07574e7bde71321cb785282b20cc821e951132149eeceeea32ddebdbf0598e'
    ModelUrl = 'https://huggingface.co/ggml-org/Clef-Flash-GGUF/resolve/8aa35d1cc7e141f3771e564eeb630a501597c681/Clef-Flash-Q4_K_M.gguf'
    ModelBytes = 6486448288L
    ModelSha256 = '3626116623ca8d89641952471fac9ce12af84fb3517520029a2ac6f5146868a2'
}

function Get-ClefRuntimeAsset([string]$Backend) {
    if ($Backend -eq 'vulkan') {
        return @{ Url = $ClefAsset.VulkanUrl; File = $ClefAsset.VulkanFile; Bytes = $ClefAsset.VulkanBytes; Sha256 = $ClefAsset.VulkanSha256; Directory = 'llama-b11669-vulkan' }
    }
    return @{ Url = $ClefAsset.RuntimeUrl; File = $ClefAsset.RuntimeFile; Bytes = $ClefAsset.RuntimeBytes; Sha256 = $ClefAsset.RuntimeSha256; Directory = 'llama-b11669-cpu' }
}

function Assert-ClefFile([string]$Path, [long]$Bytes, [string]$Sha256) {
    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) { throw "Missing local asset: $Path. Run Setup-ClefLocal.ps1 first." }
    if ((Get-Item -LiteralPath $Path).Length -ne $Bytes) { throw "Wrong asset size: $Path. File will not be used." }
    if ((Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash -ine $Sha256) { throw "SHA-256 mismatch: $Path. File will not be used." }
}

function Assert-ClefRuntime([string]$Archive, [string]$Directory, [string]$Backend = 'cpu') {
    $asset = Get-ClefRuntimeAsset $Backend
    Assert-ClefFile $Archive $asset.Bytes $asset.Sha256
    Add-Type -AssemblyName System.IO.Compression.FileSystem
    $zip = [IO.Compression.ZipFile]::OpenRead($Archive)
    $expected = @{}
    try {
        $prefix = [IO.Path]::GetFullPath($Directory).TrimEnd('\') + '\'
        foreach ($entry in $zip.Entries) {
            if (-not $entry.Name) { continue }
            $target = [IO.Path]::GetFullPath((Join-Path $Directory $entry.FullName))
            if (-not $target.StartsWith($prefix, [StringComparison]::OrdinalIgnoreCase)) { throw 'Unsafe archive path rejected.' }
            Assert-DPath $target
            if (-not (Test-Path -LiteralPath $target -PathType Leaf)) { throw 'Runtime extraction is incomplete. Re-extract the pinned archive into an empty runtime directory.' }
            if ((Get-Item -LiteralPath $target -Force).Attributes -band [IO.FileAttributes]::ReparsePoint) { throw 'Runtime symbolic links are not allowed.' }
            $stream = $entry.Open()
            $sha = [Security.Cryptography.SHA256]::Create()
            try { $expectedHash = [BitConverter]::ToString($sha.ComputeHash($stream)).Replace('-', '') }
            finally { $stream.Dispose(); $sha.Dispose() }
            if ((Get-FileHash -LiteralPath $target -Algorithm SHA256).Hash -ine $expectedHash) { throw 'Runtime file differs from the verified archive; refusing execution.' }
            $expected[$target] = $true
        }
        foreach ($file in Get-ChildItem -LiteralPath $Directory -Recurse -File) {
            if ($file.Extension -in @('.exe', '.dll') -and -not $expected.ContainsKey($file.FullName)) { throw 'Unexpected runtime executable or DLL; refusing execution.' }
        }
    }
    finally { $zip.Dispose() }
    $servers = @(Get-ChildItem -LiteralPath $Directory -Recurse -File -Filter 'llama-server.exe')
    if ($servers.Count -ne 1) { throw 'Expected exactly one llama-server.exe in the pinned runtime.' }
    return $servers[0].FullName
}
