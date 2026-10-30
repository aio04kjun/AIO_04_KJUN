param(
    [switch]$Demo,
    [ValidateRange(1, 65535)][int]$Port = 8000,
    [switch]$Check
)

$ErrorActionPreference = 'Stop'
$projectPath = $PSScriptRoot
$originalPythonPath = $env:PYTHONPATH
$shopExitCode = 0
$candidates = @()
$localPython = Join-Path $projectPath '.venv\Scripts\python.exe'
if (Test-Path -LiteralPath $localPython) {
    $candidates += @{ Path = $localPython; Prefix = @(); Bundled = $false }
}
$systemPython = Get-Command python -ErrorAction SilentlyContinue
if ($systemPython -and $systemPython.Source -notlike '*WindowsApps*') {
    $candidates += @{ Path = $systemPython.Source; Prefix = @(); Bundled = $false }
}
$launcher = Get-Command py -ErrorAction SilentlyContinue
if ($launcher) {
    $candidates += @{ Path = $launcher.Source; Prefix = @('-3'); Bundled = $false }
}
$bundledPython = Join-Path $env:USERPROFILE '.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
if (Test-Path -LiteralPath $bundledPython) {
    $candidates += @{ Path = $bundledPython; Prefix = @(); Bundled = $true }
}

try {
    $selectedRunner = $null
    foreach ($candidate in $candidates) {
        $env:PYTHONPATH = $originalPythonPath
        if ($candidate.Bundled) {
            $localDependencies = Join-Path (Split-Path -Parent $projectPath) '.supabase-deps'
            if (Test-Path -LiteralPath $localDependencies) {
                $env:PYTHONPATH = "$localDependencies;$originalPythonPath"
            }
        }
        $runnerPath = $candidate.Path
        $runnerPrefix = $candidate.Prefix
        $available = $false
        try {
            & $runnerPath @runnerPrefix -c 'import fastapi, uvicorn, httpx, pydantic' 2>$null
            $available = $LASTEXITCODE -eq 0
        } catch { $available = $false }
        if ($available) {
            $selectedRunner = $candidate
            break
        }
    }
    if (-not $selectedRunner) {
        throw 'Python dependencies not found. See docs/run-guide.md: create .venv and install requirements.txt.'
    }
    Write-Host "Python: $($selectedRunner.Path)"
    if ($Check) {
        Write-Host 'OK: FastAPI / Uvicorn / HTTPX / Pydantic available.'
        exit 0
    }
    $runnerPath = $selectedRunner.Path
    $runnerPrefix = $selectedRunner.Prefix
    $runScript = Join-Path $projectPath 'run.py'
    $runArguments = @($runScript, '--port', "$Port")
    if ($Demo) { $runArguments += '--demo' }
    Write-Host "Open http://localhost:$Port (Ctrl+C to stop)"
    Push-Location -LiteralPath $projectPath
    try { & $runnerPath @runnerPrefix @runArguments; $shopExitCode = $LASTEXITCODE }
    finally { Pop-Location }
} finally {
    $env:PYTHONPATH = $originalPythonPath
}
exit $shopExitCode
