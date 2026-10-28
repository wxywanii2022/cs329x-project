# Run without installing a package or downloading a Python interpreter.
param([Parameter(ValueFromRemainingArguments = $true)][string[]]$SimulatorArgs)
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$interpreter = Join-Path $projectRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $interpreter)) {
    if (Get-Command uv -ErrorAction SilentlyContinue) {
        $interpreter = & uv --cache-dir (Join-Path $projectRoot '.cache\uv') python find --offline --no-python-downloads '>=3.11'
        if ($LASTEXITCODE -ne 0) { throw 'No existing Python 3.11+ found. Install Python, then create .venv.' }
    } else {
        $pythonCommand = Get-Command python -ErrorAction SilentlyContinue
        if (-not $pythonCommand) { throw 'Python 3.11+ or uv is required.' }
        $interpreter = $pythonCommand.Source
    }
}
$oldPythonPath = $env:PYTHONPATH
$oldEncoding = $env:PYTHONIOENCODING
try {
    $env:PYTHONPATH = Join-Path $projectRoot 'src'
    $env:PYTHONIOENCODING = 'utf-8'
    Push-Location -LiteralPath $projectRoot
    try {
        & $interpreter -m adaptive_tutor @SimulatorArgs
        $result = $LASTEXITCODE
    } finally { Pop-Location }
} finally {
    $env:PYTHONPATH = $oldPythonPath
    $env:PYTHONIOENCODING = $oldEncoding
}
exit $result
