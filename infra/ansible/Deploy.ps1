#Requires -Version 5.1
<#
.SYNOPSIS
  Déploiement en une commande de RESILIENCE-ALPHA (Windows + Docker Desktop).
.DESCRIPTION
  Ansible (conteneur éphémère) fait le preflight et la vérification ; Docker Compose est lancé
  depuis WINDOWS pour le déploiement, afin que les bind mounts (WAF, Grafana, Loki, Alloy)
  se résolvent comme dans un déploiement manuel. Ne fait jamais `down -v`, ne supprime aucun
  volume et ne remet pas la base à zéro (voir scripts/reset_demo.sh pour cela).
  Prérequis : .env à la racine (voir README, scripts/render_env.sh).
.EXAMPLE
  .\infra\ansible\Deploy.ps1 -CheckOnly
.EXAMPLE
  .\infra\ansible\Deploy.ps1
#>
[CmdletBinding()]
param(
    [switch]$CheckOnly,
    [switch]$VerifyOnly,
    [switch]$SkipBuild
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

if ($CheckOnly -and $VerifyOnly) {
    throw 'Utiliser -CheckOnly ou -VerifyOnly, pas les deux.'
}

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$ansibleDir = $PSScriptRoot
$envFile = Join-Path $repoRoot '.env'
$appCompose = Join-Path $repoRoot 'infra\compose\docker-compose.yml'
$obsCompose = Join-Path $repoRoot 'infra\compose\docker-compose.observability.yml'
$modelsDir = Join-Path $repoRoot 'ml\models'
$modelFile = Join-Path $modelsDir 'isolation_forest.joblib'
$image = 'resilience-ansible:1.0'

function Invoke-Checked {
    param(
        [Parameter(Mandatory = $true)][string]$Executable,
        [Parameter(Mandatory = $true)][string[]]$Arguments
    )
    & $Executable @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "$Executable a échoué (code $LASTEXITCODE)"
    }
}

function Invoke-Ansible {
    param(
        [Parameter(Mandatory = $true)][string]$Tag,
        [switch]$NeedsDockerSocket
    )
    $argsList = @(
        'run', '--rm',
        '--mount', "type=bind,source=$repoRoot,target=/workspace,readonly",
        '--workdir', '/workspace'
    )
    if ($NeedsDockerSocket) {
        # Ce socket donne un accès complet au démon Docker (en lecture seule ou non, un
        # montage `ro` ne limite pas les appels API). Acceptable pour un conteneur
        # éphémère lancé à la main, jamais pour un runner permanent ni pour un
        # conteneur exposé. Le moteur de remédiation, lui, passe par un docker-socket-proxy.
        $argsList += @('--mount', 'type=bind,source=/var/run/docker.sock,target=/var/run/docker.sock')
    }
    $argsList += @(
        $image,
        '-i', '/opt/resilience-ansible/inventory.ini',
        '/opt/resilience-ansible/site.yml',
        '--tags', $Tag
    )
    Invoke-Checked -Executable 'docker' -Arguments $argsList
}

function Test-Transaction {
    # Même sonde que scripts/check_transaction.sh, rejouée depuis le conteneur de remédiation
    # (l'API n'est pas publiée sur l'hôte) : l'API répond ET une transaction de test passe.
    Invoke-Checked -Executable 'docker' -Arguments @(
        'compose', '--env-file', $envFile, '-f', $appCompose,
        'exec', '-T',
        '-e', 'FROM_ACCOUNT=TEST-0001', '-e', 'TO_ACCOUNT=TEST-0002', '-e', 'AMOUNT_CENTS=100',
        'remediation', 'python', '-m', 'app.cli.check_transaction'
    )
}

$engineOS = (& docker info --format '{{.OSType}}').Trim()
if ($LASTEXITCODE -ne 0) {
    throw 'Docker Desktop ne tourne pas ou est injoignable.'
}
if ($engineOS -ne 'linux') {
    throw 'Passer Docker Desktop en conteneurs Linux avant de construire le runner Ansible.'
}

if (-not $SkipBuild) {
    Write-Host '[build] Construction de l''image Ansible...'
    Invoke-Checked -Executable 'docker' -Arguments @('build', '-t', $image, '-f', (Join-Path $ansibleDir 'Dockerfile'), $ansibleDir)
}

if ($VerifyOnly) {
    Write-Host '[verify] Vérification des services...'
    Invoke-Ansible -Tag 'verify' -NeedsDockerSocket
    Test-Transaction
    Write-Host '[ok] Services en marche et transaction de test réussie.'
    exit 0
}

Write-Host '[preflight] Contrôle de .env et des deux Compose...'
Invoke-Ansible -Tag 'preflight'
if ($CheckOnly) {
    Write-Host '[ok] Preflight réussi. Rien n''a été déployé.'
    exit 0
}

# Un clone neuf n'a pas de modèle (ml/models/* est ignoré par Git) et le détecteur refuse de
# démarrer sans lui. Même procédure que le README : `docker run` et non `compose run`, car le
# service monte /models en lecture seule.
if (-not (Test-Path $modelFile)) {
    Write-Host '[ml] Modèle absent : entraînement sur ml/data/normal.csv...'
    New-Item -ItemType Directory -Force -Path $modelsDir | Out-Null
    Invoke-Checked -Executable 'docker' -Arguments @('compose', '--env-file', $envFile, '-f', $appCompose, 'build', 'anomaly-detector')
    Invoke-Checked -Executable 'docker' -Arguments @(
        'run', '--rm', '--env-file', $envFile,
        '-v', "$(Join-Path $repoRoot 'ml\data'):/data:ro",
        '-v', "${modelsDir}:/models",
        '-e', 'DATASET_PATH=/data/normal.csv',
        '-e', 'MODEL_PATH=/models/isolation_forest.joblib',
        'resilience-alpha/anomaly-detector:dev', 'python', '-m', 'app.cli', 'train'
    )
}

Write-Host '[deploy] Socle applicatif (Compose Windows)...'
Invoke-Checked -Executable 'docker' -Arguments @('compose', '--env-file', $envFile, '-f', $appCompose, 'up', '-d', '--build', '--wait')

Write-Host '[deploy] Observabilité (Compose Windows, après le socle qui crée resilience-net)...'
Invoke-Checked -Executable 'docker' -Arguments @('compose', '--env-file', $envFile, '-f', $obsCompose, 'up', '-d', '--wait')

Write-Host '[verify] Vérification des services par Ansible...'
Invoke-Ansible -Tag 'verify' -NeedsDockerSocket
Test-Transaction
Write-Host '[ok] Déploiement terminé : services en marche et transaction de test réussie.'
