# Configure Ollama environment
$ollamaDir = if (Get-Command ollama -ErrorAction SilentlyContinue) { Split-Path (Get-Command ollama).Source } else { "$env:LOCALAPPDATA\Programs\Ollama" }
$modelsDir = if ($env:OLLAMA_MODELS) { $env:OLLAMA_MODELS } else { "$env:USERPROFILE\.ollama\models" }

if (-not (Test-Path $modelsDir)) {
    New-Item -ItemType Directory -Path $modelsDir -Force | Out-Null
}

# Set User environment variable for OLLAMA_MODELS
[System.Environment]::SetEnvironmentVariable("OLLAMA_MODELS", $modelsDir, "User")
$env:OLLAMA_MODELS = $modelsDir

# Add to user PATH if not present
$userPath = [System.Environment]::GetEnvironmentVariable("Path", "User")
if ($userPath -notlike "*$ollamaDir*") {
    [System.Environment]::SetEnvironmentVariable("Path", "$userPath;$ollamaDir", "User")
}
$env:Path = "$env:Path;$ollamaDir"

Write-Output "OLLAMA_MODELS: $env:OLLAMA_MODELS"
& "$ollamaDir\ollama.exe" --version

