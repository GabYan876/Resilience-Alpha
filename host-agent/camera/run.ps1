#Requires -Version 5.1
<#
.SYNOPSIS
  Lance l'agent caméra natif du PC Hôte (hors Docker : Docker Desktop ne voit pas la caméra USB).
.DESCRIPTION
  Crée le venv et télécharge les modèles au premier lancement. Variables attendues :
    AGENT_TOKEN        jeton partagé avec `auth` (HOST_AGENT_TOKEN dans .env), 32 caractères minimum ;
                     relu dans le .env racine s'il n'est pas défini
    TEMPLATE_KEY_FILE  fichier de clé des gabarits (créé par `python -m app.cli genkey <fichier>`)
  Option : -BindAddress, IP du PC Hôte joignable par Docker (défaut : 0.0.0.0 restreint au pare-feu
  Windows : n'autoriser que le sous-réseau Docker / hotspot). Ne jamais exposer ce port hors du PC Hôte.
.EXAMPLE
  $env:AGENT_TOKEN = '...'; $env:TEMPLATE_KEY_FILE = '.\data\template.key'; .\run.ps1
#>
[CmdletBinding()]
param(
    [string]$BindAddress = '0.0.0.0',
    [int]$Port = 8765
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot

# Par défaut, le jeton est relu dans le .env racine (HOST_AGENT_TOKEN, produit par render_env.sh) et la clé
# des gabarits dans data\template.key : un seul jeton à tenir, identique des deux côtés.
$envFile = Join-Path $PSScriptRoot '..\..\.env'
if (-not $env:AGENT_TOKEN -and (Test-Path $envFile)) {
    $line = Select-String -Path $envFile -Pattern '^HOST_AGENT_TOKEN=(.+)$' | Select-Object -First 1
    if ($line) { $env:AGENT_TOKEN = $line.Matches[0].Groups[1].Value.Trim() }
}
if (-not $env:TEMPLATE_KEY_FILE -and (Test-Path '.\data\template.key')) { $env:TEMPLATE_KEY_FILE = '.\data\template.key' }
if (-not $env:AGENT_TOKEN) { throw 'AGENT_TOKEN manquant' }
if (-not $env:TEMPLATE_KEY_FILE) { throw 'TEMPLATE_KEY_FILE manquant (python -m app.cli genkey <fichier>)' }

if (-not (Test-Path '.venv')) {
    python -m venv .venv
    & .\.venv\Scripts\python.exe -m pip install -q -r requirements.txt
}
& .\.venv\Scripts\python.exe scripts\download_models.py
if ($LASTEXITCODE -ne 0) { throw 'modèles indisponibles' }

& .\.venv\Scripts\python.exe -m uvicorn app.main:create_app --factory --host $BindAddress --port $Port
