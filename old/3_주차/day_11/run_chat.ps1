$ErrorActionPreference = 'Stop'
$scriptPath = Join-Path $PSScriptRoot 'lmstudio_chat.py'
$pythonCommand = Get-Command python -ErrorAction SilentlyContinue
$pyCommand = Get-Command py -ErrorAction SilentlyContinue
$bundledPython = Join-Path $env:USERPROFILE '.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
if ($pythonCommand) {
    & $pythonCommand.Source $scriptPath @args
} elseif ($pyCommand) {
    & $pyCommand.Source -3 $scriptPath @args
} elseif (Test-Path -LiteralPath $bundledPython) {
    & $bundledPython $scriptPath @args
} else {
    throw 'Python 3.10 or later is required. Install Python and enable Add python.exe to PATH.'
}
exit $LASTEXITCODE
