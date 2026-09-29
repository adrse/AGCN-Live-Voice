$ErrorActionPreference = "Stop"

Write-Host "AGCN Live Voice - Setup Qwen/Ollama"

$ollama = Get-Command ollama -ErrorAction SilentlyContinue

if (-not $ollama) {
    Write-Host "Ollama nao encontrado."
    $winget = Get-Command winget -ErrorAction SilentlyContinue
    if ($winget) {
        Write-Host "Instalando Ollama pelo winget..."
        winget install --id Ollama.Ollama -e --accept-source-agreements --accept-package-agreements
        Write-Host "Se o comando ollama ainda nao estiver disponivel, feche e abra o terminal."
        exit 2
    } else {
        Write-Host "Instale Ollama manualmente e execute este script novamente."
        exit 2
    }
}

Write-Host "Ollama encontrado:"
ollama --version

$list = ollama list | Out-String
if ($list -notmatch "qwen3:4b") {
    Write-Host "Baixando qwen3:4b..."
    ollama pull qwen3:4b
} else {
    Write-Host "qwen3:4b ja instalado."
}

Write-Host ""
Write-Host "Modelos:"
ollama list

Write-Host ""
Write-Host "Setup Qwen concluido."
