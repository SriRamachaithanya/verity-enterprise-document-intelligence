$modelsDir = if ($env:OLLAMA_MODELS) { $env:OLLAMA_MODELS } else { "$env:USERPROFILE\.ollama\models" }
$ollamaExe = if (Get-Command ollama -ErrorAction SilentlyContinue) { (Get-Command ollama).Source } else { "$env:LOCALAPPDATA\Programs\Ollama\ollama.exe" }
$env:OLLAMA_MODELS = $modelsDir

$existing = Get-Process -Name "ollama" -ErrorAction SilentlyContinue
if (-not $existing) {
    # Launch detached with OLLAMA_MODELS environment variable
    $psi = New-Object System.Diagnostics.ProcessStartInfo
    $psi.FileName = $ollamaExe
    $psi.Arguments = "serve"
    $psi.WindowStyle = [System.Diagnostics.ProcessWindowStyle]::Hidden
    $psi.EnvironmentVariables["OLLAMA_MODELS"] = $modelsDir
    $psi.UseShellExecute = $false
    [System.Diagnostics.Process]::Start($psi) | Out-Null
    Start-Sleep -Seconds 3
}

try {
    $res = Invoke-RestMethod -Uri "http://127.0.0.1:11434/api/tags" -Method Get
    Write-Output "Ollama API is responding on http://127.0.0.1:11434"
    $modelNames = ($res.models | ForEach-Object { $_.name }) -join ", "
    Write-Output "Available models: $modelNames"
} catch {
    Write-Error "Failed to connect to Ollama: $_"
}
