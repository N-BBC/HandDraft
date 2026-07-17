param(
    [int]$Port = 8017,
    [string]$HostAddress = "127.0.0.1"
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$candidates = @(
    $env:HANDDRAFT_PYTHON,
    (Join-Path $ProjectRoot ".venv\Scripts\python.exe"),
    "C:\Users\Administrator\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe",
    "python"
) | Where-Object { $_ }

$python = $null
foreach ($candidate in $candidates) {
    try {
        & $candidate --version *> $null
        if ($LASTEXITCODE -eq 0) {
            $python = $candidate
            break
        }
    } catch {
        continue
    }
}

if (-not $python) {
    throw "No working Python runtime was found. Install Python 3.11+ and run pip install -r requirements.txt."
}

$runtimePackages = Join-Path $ProjectRoot ".runtime"
if (Test-Path -LiteralPath $runtimePackages) {
    $env:PYTHONPATH = "$runtimePackages;$ProjectRoot;$env:PYTHONPATH"
}

Set-Location $ProjectRoot
& $python -m uvicorn handdraft.main:app --host $HostAddress --port $Port
