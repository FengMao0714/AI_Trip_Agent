[CmdletBinding()]
param(
    [switch]$DockerOnly,
    [switch]$UseProxy,
    [switch]$NoProxy,
    [string]$ProxyUrl = "http://127.0.0.1:10808",
    [string]$NoProxyHosts = "token-plan-cn.xiaomimimo.com,localhost,127.0.0.1,::1",
    [int]$BackendPort = 8000,
    [int]$FrontendPort = 3000,
    [int]$PostgresHostPort = 15432,
    [int]$RedisHostPort = 16379
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$RootDir = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$BackendDir = Join-Path $RootDir "backend"
$FrontendDir = Join-Path $RootDir "frontend"

function Write-Step {
    param([string]$Message)
    Write-Host ""
    Write-Host "==> $Message" -ForegroundColor Cyan
}

function Assert-Command {
    param([string]$Name)
    if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
        throw "Command '$Name' was not found. Please install it or add it to PATH."
    }
}

function Test-DockerDaemon {
    $previousErrorActionPreference = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    try {
        & docker info > $null 2>&1
        return $LASTEXITCODE -eq 0
    } catch {
        return $false
    } finally {
        $ErrorActionPreference = $previousErrorActionPreference
    }
}

function Start-DockerDesktopIfNeeded {
    if (Test-DockerDaemon) {
        Write-Host "Docker daemon is running." -ForegroundColor Green
        return
    }

    Write-Host "Docker daemon is not running. Trying to start Docker Desktop..." -ForegroundColor Yellow

    $dockerDesktopCandidates = @(
        "$env:ProgramFiles\Docker\Docker\Docker Desktop.exe",
        "${env:ProgramFiles(x86)}\Docker\Docker\Docker Desktop.exe",
        "$env:LOCALAPPDATA\Docker\Docker Desktop.exe"
    )

    $dockerDesktopPath = $dockerDesktopCandidates |
        Where-Object { $_ -and (Test-Path $_) } |
        Select-Object -First 1

    if (-not $dockerDesktopPath) {
        throw "Docker Desktop is not running, and Docker Desktop.exe was not found. Please start Docker Desktop manually, then run this script again."
    }

    Start-Process -FilePath $dockerDesktopPath -WindowStyle Hidden

    $timeoutSeconds = 180
    $deadline = (Get-Date).AddSeconds($timeoutSeconds)
    while ((Get-Date) -lt $deadline) {
        if (Test-DockerDaemon) {
            Write-Host "Docker daemon is running." -ForegroundColor Green
            return
        }
        Write-Host "Waiting for Docker Desktop..."
        Start-Sleep -Seconds 5
    }

    throw "Timed out waiting for Docker Desktop. Please open Docker Desktop, wait until it says it is running, then run this script again."
}

function Invoke-DockerCompose {
    param([Parameter(Mandatory = $true)][string[]]$ComposeArgs)

    & docker compose @ComposeArgs
    if ($LASTEXITCODE -ne 0) {
        throw "docker compose $($ComposeArgs -join ' ') failed with exit code $LASTEXITCODE."
    }
}

function Wait-ComposeServiceHealthy {
    param(
        [string]$Service,
        [int]$TimeoutSeconds = 60
    )

    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    while ((Get-Date) -lt $deadline) {
        $rawContainerId = & docker compose ps -q $Service 2>$null
        $containerId = ($rawContainerId | Select-Object -First 1)
        if ($null -ne $containerId) {
            $containerId = $containerId.ToString().Trim()
        }
        if ($containerId) {
            $rawHealth = & docker inspect -f "{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}" $containerId 2>$null
            $health = ($rawHealth | Select-Object -First 1)
            if ($null -ne $health) {
                $health = $health.ToString().Trim()
            }
            if ($health -eq "healthy" -or $health -eq "running") {
                Write-Host "$Service is $health." -ForegroundColor Green
                return
            }
            Write-Host "$Service is $health; waiting..."
        }
        Start-Sleep -Seconds 2
    }

    throw "Timed out waiting for Docker service '$Service' to become healthy."
}

function New-BackendCommand {
    $proxyBlock = if (-not $NoProxy) {
        @"
`$env:HTTP_PROXY='$ProxyUrl'
`$env:HTTPS_PROXY='$ProxyUrl'
`$env:http_proxy='$ProxyUrl'
`$env:https_proxy='$ProxyUrl'
`$env:NO_PROXY='$NoProxyHosts'
`$env:no_proxy='$NoProxyHosts'
"@
    } else {
        @"
Remove-Item Env:HTTP_PROXY,Env:HTTPS_PROXY,Env:ALL_PROXY,Env:http_proxy,Env:https_proxy,Env:all_proxy,Env:NO_PROXY,Env:no_proxy -ErrorAction SilentlyContinue
"@
    }

    @"
Set-Location '$BackendDir'
`$env:POSTGRES_HOST='localhost'
`$env:POSTGRES_PORT='$PostgresHostPort'
`$env:REDIS_HOST='localhost'
`$env:REDIS_PORT='$RedisHostPort'
$proxyBlock
Write-Host 'Backend: http://127.0.0.1:$BackendPort' -ForegroundColor Green
uv run uvicorn app.main:app --host 127.0.0.1 --port $BackendPort --reload
"@
}

function New-FrontendCommand {
    @"
Set-Location '$FrontendDir'
`$env:NEXT_PUBLIC_API_URL='http://localhost:$BackendPort'
if (-not (Test-Path 'node_modules')) {
    Write-Host 'Installing frontend dependencies...' -ForegroundColor Yellow
    corepack enable
    corepack pnpm install --frozen-lockfile
}
Write-Host 'Frontend: http://localhost:$FrontendPort/chat' -ForegroundColor Green
corepack pnpm exec next dev -H 127.0.0.1 -p $FrontendPort
"@
}

Write-Step "Checking prerequisites"
Assert-Command docker
Assert-Command uv
Assert-Command node
Assert-Command corepack
Start-DockerDesktopIfNeeded

Set-Location $RootDir
$env:POSTGRES_HOST_PORT = $PostgresHostPort.ToString()
$env:REDIS_HOST_PORT = $RedisHostPort.ToString()

if ($DockerOnly) {
    Write-Step "Starting full Docker stack"
    Invoke-DockerCompose -ComposeArgs @("up", "--detach", "--build")
    Wait-ComposeServiceHealthy "postgres"
    Wait-ComposeServiceHealthy "redis"
    Write-Host ""
    Write-Host "Docker stack started." -ForegroundColor Green
    Write-Host "Frontend: http://localhost:3000/chat"
    Write-Host "Backend:  http://localhost:8000"
    return
}

Write-Step "Starting Docker infrastructure: postgres + redis"
Invoke-DockerCompose -ComposeArgs @("up", "--detach", "postgres", "redis")
Wait-ComposeServiceHealthy "postgres"
Wait-ComposeServiceHealthy "redis"

Write-Step "Opening backend and frontend terminals"
$backendCommand = New-BackendCommand
$frontendCommand = New-FrontendCommand

Start-Process powershell.exe -ArgumentList @(
    "-NoExit",
    "-ExecutionPolicy", "Bypass",
    "-Command", $backendCommand
)

Start-Process powershell.exe -ArgumentList @(
    "-NoExit",
    "-ExecutionPolicy", "Bypass",
    "-Command", $frontendCommand
)

Write-Host ""
Write-Host "Started AI Trip Agent." -ForegroundColor Green
Write-Host "Backend:  http://127.0.0.1:$BackendPort"
Write-Host "Frontend: http://localhost:$FrontendPort/chat"
Write-Host ""
if ($UseProxy) {
    Write-Host "Proxy is enabled through $ProxyUrl." -ForegroundColor Yellow
    Write-Host "NO_PROXY keeps model service direct: $NoProxyHosts"
} elseif (-not $NoProxy) {
    Write-Host "Proxy is enabled for Hugging Face through $ProxyUrl." -ForegroundColor Yellow
    Write-Host "NO_PROXY keeps model service direct: $NoProxyHosts"
} else {
    Write-Host "Proxy is disabled for backend." -ForegroundColor Yellow
}
Write-Host ""
Write-Host "Stop services:"
Write-Host "  Close the backend/frontend terminal windows"
Write-Host "  docker compose stop postgres redis"
