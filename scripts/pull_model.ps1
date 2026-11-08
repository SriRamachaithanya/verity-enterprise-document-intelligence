$ollamaExe = if (Get-Command ollama -ErrorAction SilentlyContinue) { (Get-Command ollama).Source } else { "$env:LOCALAPPDATA\Programs\Ollama\ollama.exe" }
$modelsDir = if ($env:OLLAMA_MODELS) { $env:OLLAMA_MODELS } else { "$env:USERPROFILE\.ollama\models" }
$env:OLLAMA_MODELS = $modelsDir

Write-Output "Pulling qwen2.5:1.5b using Ollama ($ollamaExe)..."
& $ollamaExe pull qwen2.5:1.5b

