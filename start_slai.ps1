$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $PSScriptRoot

try {
    Write-Host "[1/3] Checking Python..."
    if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
        throw "Python was not found in PATH."
    }

    & python --version
    if ($LASTEXITCODE -ne 0) {
        throw "Python could not start."
    }

    Write-Host "[2/3] Checking local Ollama..."
    $tagsUrl = "http://127.0.0.1:11434/api/tags"
    $models = $null

    try {
        $models = Invoke-RestMethod -Uri $tagsUrl -TimeoutSec 5
    }
    catch {
        if (-not (Get-Command ollama -ErrorAction SilentlyContinue)) {
            throw "Ollama is unavailable and its command was not found."
        }

        Write-Host "Starting Ollama..."
        Start-Process -FilePath "ollama" -ArgumentList "serve" | Out-Null

        for ($attempt = 1; $attempt -le 15; $attempt++) {
            Start-Sleep -Seconds 2
            try {
                $models = Invoke-RestMethod -Uri $tagsUrl -TimeoutSec 3
                break
            }
            catch {
                $models = $null
            }
        }
    }

    if ($null -eq $models) {
        throw "Local Ollama did not become available."
    }

    $requiredModel = "slai-logistics-fast:latest"
    if ($requiredModel -notin @($models.models.name)) {
        throw "Required model is missing: $requiredModel"
    }

    Write-Host "[3/3] Starting SLAI..."
    Write-Host "Open: http://127.0.0.1:8080/index.html"
    Write-Host "Stop SLAI: Ctrl+C"

    & python -u .\slai_server.py

    if ($LASTEXITCODE -ne 0) {
        throw "SLAI stopped with exit code $LASTEXITCODE. See the error above."
    }
}
catch {
    Write-Host ""
    Write-Host ("START FAILED: " + $_.Exception.Message) -ForegroundColor Red
    exit 1
}
