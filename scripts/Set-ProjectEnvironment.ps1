[CmdletBinding()]
param(
    [string]$StorageRoot = (Split-Path -Parent $PSScriptRoot)
)

$ErrorActionPreference = 'Stop'
$root = [IO.Path]::GetFullPath($StorageRoot)
if ([IO.Path]::GetPathRoot($root) -ine 'D:\') {
    throw 'Project storage must be on D:. Pass -StorageRoot D:\your\project before downloading or installing anything.'
}

# Refuse junction/symlink redirection, including existing ancestors and cache paths.
function Assert-DPath([string]$Path) {
    $full = [IO.Path]::GetFullPath($Path)
    if ([IO.Path]::GetPathRoot($full) -ine 'D:\') { throw 'Storage path must remain on D:.' }
    $item = $full
    while ($item) {
        if (Test-Path -LiteralPath $item) {
            if ((Get-Item -LiteralPath $item -Force).Attributes -band [IO.FileAttributes]::ReparsePoint) {
                throw 'Project storage must not use junctions or symbolic links.'
            }
        }
        $parent = Split-Path -Parent $item
        if ($parent -eq $item) { break }
        $item = $parent
    }
}

Assert-DPath $root
$folders = @{
    TEMP = 'cache\temp'; TMP = 'cache\temp'; TMPDIR = 'cache\temp'
    PIP_CACHE_DIR = 'cache\pip'; HF_HOME = 'cache\huggingface'
    HF_HUB_CACHE = 'cache\huggingface\hub'; HF_XET_CACHE = 'cache\huggingface\xet'
    TORCH_HOME = 'cache\torch'; XDG_CACHE_HOME = 'cache\xdg'
    LLAMA_CACHE = 'cache\llama'; UV_CACHE_DIR = 'cache\uv'
}
foreach ($name in $folders.Keys) { Assert-DPath (Join-Path $root $folders[$name]) }
foreach ($name in $folders.Keys) {
    $value = Join-Path $root $folders[$name]
    New-Item -ItemType Directory -Path $value -Force | Out-Null
    [Environment]::SetEnvironmentVariable($name, $value, 'Process')
}
foreach ($relative in @('cache\downloads', 'runtime', 'models\clef-flash', 'outputs\clef-cpu')) {
    $path = Join-Path $root $relative
    Assert-DPath $path
    New-Item -ItemType Directory -Path $path -Force | Out-Null
}

# No user/machine environment, registry, PATH, driver or global installation changes.
[pscustomobject]@{
    StorageRoot = $root
    DownloadDirectory = Join-Path $root 'cache\downloads'
    RuntimeRoot = Join-Path $root 'runtime'
    ModelPath = Join-Path $root 'models\clef-flash\Clef-Flash-Q4_K_M.gguf'
}
