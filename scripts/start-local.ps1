#Requires -Version 5.1
<#
.SYNOPSIS
    info-ai local dev one-click start (Windows)
.DESCRIPTION
    Starts 4 backend services:
      1. info_aggregation - Python crawl + analysis (port 8000)
      2. info-serve       - Go API gateway (port 8085)
      3. info-admin       - Vue3 admin panel (port 5174)
      4. info-mvp         - uni-app H5 client (port 5175)
    A service failure does not block others.
    Does NOT start MySQL or Docker.
.EXAMPLE
    .\scripts\start-local.ps1
    .\scripts\start-local.ps1 -MySQLPassword 123456
#>

[CmdletBinding()]
param(
    [string]$MySQLHost       = "127.0.0.1",
    [string]$MySQLPort       = "3306",
    [string]$MySQLUser       = "root",
    [string]$MySQLPassword   = "123456",
    [string]$MySQLDB         = "info-max",
    [string]$RedisHost       = "127.0.0.1",
    [string]$RedisPort       = "6379",
    [string]$RedisPassword   = "",
    [string]$AggregationPort = "8000",
    [string]$InfoServePort   = "8085",
    [string]$InfoAdminPort   = "5174",
    [string]$InfoMvpPort     = "5175"
)

$ErrorActionPreference = "Continue"

$ROOT_DIR = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$LOG_DIR  = Join-Path $ROOT_DIR "logs\local"
New-Item -ItemType Directory -Path $LOG_DIR -Force | Out-Null

$script:Failed = [System.Collections.Generic.List[string]]::new()

function Write-Step([string]$msg) {
    Write-Host "" ; Write-Host "==> $msg" -ForegroundColor Cyan
}
function Write-Ok([string]$msg)   { Write-Host "  OK   $msg" -ForegroundColor Green }
function Write-Warn([string]$msg) { Write-Host "  WARN $msg" -ForegroundColor Yellow }
function Write-Fail([string]$msg) { Write-Host "  FAIL $msg" -ForegroundColor Red }

# ============================================================
# helper: start a background service via a temp .cmd wrapper
# ============================================================
function Start-Bg {
    [CmdletBinding()]
    param(
        [string]$Name,
        [string]$WorkDir,
        [string]$Command,
        [string]$Arguments,
        [hashtable]$EnvVars,
        [switch]$SelfLog
    )

    Write-Step "start $Name"

    $logFile  = Join-Path $LOG_DIR "$Name.log"
    $errFile  = Join-Path $LOG_DIR "$Name.err.log"
    $pidFile  = Join-Path $LOG_DIR "$Name.pid"
    $cmdFile  = Join-Path $LOG_DIR "$Name.cmd"

    # build a temp .cmd file: set env vars then run the command
    $cmdLines = [System.Collections.Generic.List[string]]::new()
    $cmdLines.Add("@echo off")
    $cmdLines.Add("chcp 65001 >nul 2>&1")
    foreach ($key in $EnvVars.Keys) {
        $val = $EnvVars[$key]
        $cmdLines.Add("set `"$key=$val`"")
    }
    $cmdLines.Add("`"$Command`" $Arguments")
    [System.IO.File]::WriteAllLines($cmdFile, $cmdLines, (New-Object System.Text.UTF8Encoding $false))

    try {
        if ($SelfLog) {
            # Process manages its own log files (e.g. launch.py redirects stdout/stderr internally)
            $proc = Start-Process -FilePath "cmd.exe" `
                -ArgumentList "/c", $cmdFile `
                -WorkingDirectory $WorkDir `
                -WindowStyle Hidden `
                -PassThru
        } else {
            $proc = Start-Process -FilePath "cmd.exe" `
                -ArgumentList "/c", $cmdFile `
                -WorkingDirectory $WorkDir `
                -WindowStyle Hidden `
                -PassThru `
                -RedirectStandardOutput $logFile `
                -RedirectStandardError $errFile
        }

        Set-Content -Path $pidFile -Value $proc.Id -Encoding UTF8
        Write-Ok "$Name started, PID: $($proc.Id), log: $logFile"
    } catch {
        Write-Fail "$Name failed: $_"
        $script:Failed.Add($Name)
    }
}

# ============================================================
# check dependencies
# ============================================================
Write-Step "check dependencies"

$pythonVenv = Join-Path $ROOT_DIR "info_aggregation\.venv\Scripts\python.exe"
$checks = @(
    @{ Path = $pythonVenv;                                          Label = "Python venv" },
    @{ Path = (Join-Path $ROOT_DIR "info_aggregation\main.py");    Label = "main.py" },
    @{ Path = (Join-Path $ROOT_DIR "info-serve\go.mod");           Label = "go.mod" },
    @{ Path = (Join-Path $ROOT_DIR "info-admin\package.json");     Label = "admin pkg" },
    @{ Path = (Join-Path $ROOT_DIR "info-mvp\package.json");       Label = "mvp pkg" }
)

$missing = $false
foreach ($c in $checks) {
    if (Test-Path $c.Path) { Write-Ok "$($c.Label)" }
    else { Write-Fail "$($c.Label): $($c.Path)"; $missing = $true }
}
foreach ($cmd in @("go", "npm")) {
    if (Get-Command $cmd -ErrorAction SilentlyContinue) { Write-Ok "$cmd found" }
    else { Write-Fail "$cmd not found"; $missing = $true }
}
if ($missing) { Write-Fail "Missing deps, abort."; exit 1 }

# ============================================================
# check ports
# ============================================================
Write-Step "check ports"

foreach ($p in @(
    @{ Port = $AggregationPort; Name = "aggregation" },
    @{ Port = $InfoServePort;   Name = "info-serve" },
    @{ Port = $InfoAdminPort;   Name = "admin" },
    @{ Port = $InfoMvpPort;     Name = "mvp" }
)) {
    $conn = Get-NetTCPConnection -LocalPort ([int]$p.Port) -State Listen -ErrorAction SilentlyContinue
    if ($conn) {
        Write-Fail "$($p.Name) port $($p.Port) in use, PID: $($conn[0].OwningProcess)"
        Write-Host "  Run first: .\scripts\stop-local.ps1" -ForegroundColor Yellow
        exit 1
    }
    Write-Ok "$($p.Name) port $($p.Port) free"
}

# ============================================================
# check Redis
# ============================================================
Write-Step "check Redis"

$redisCheck = & $pythonVenv -c "import redis,sys; r=redis.Redis(host=sys.argv[1],port=int(sys.argv[2]),socket_timeout=3); print('OK' if r.ping() else 'FAIL')" $RedisHost $RedisPort
if ($redisCheck -eq "OK") { Write-Ok "Redis ${RedisHost}:${RedisPort}" }
else {
    Write-Fail "Redis ${RedisHost}:${RedisPort} not ready"
    Write-Host "  Start Redis first, or use -RedisHost/-RedisPort." -ForegroundColor Yellow
    exit 1
}

# ============================================================
# common vars
# ============================================================
$MYSQL_DSN   = "${MySQLUser}:${MySQLPassword}@tcp(${MySQLHost}:${MySQLPort})/${MySQLDB}?charset=utf8mb4&parseTime=true&loc=Local"
$REDIS_ADDR  = "${RedisHost}:${RedisPort}"
$GoPath      = Join-Path $ROOT_DIR ".go-path"
$GoCache     = Join-Path $ROOT_DIR ".go-build-cache"
$GoModCache  = Join-Path $GoPath "pkg\mod"

# resolve npm.cmd full path (Start-Process needs .cmd extension on Windows)
$npmCmd = (Get-Command npm -CommandType Application | Where-Object { $_.Source -like '*.cmd' } | Select-Object -First 1).Source
if (-not $npmCmd) { $npmCmd = "npm.cmd" }

# ============================================================
# 1. info_aggregation
# ============================================================
Start-Bg -Name "info_aggregation" -SelfLog `
    -WorkDir (Join-Path $ROOT_DIR "info_aggregation") `
    -Command $pythonVenv `
    -Arguments "launch.py" `
    -EnvVars @{
        APP_ENV                       = "local"
        ENABLE_PUBLIC_API             = "1"
        DB_TYPE                       = "mysql"
        DB_HOST                       = $MySQLHost
        DB_PORT                       = $MySQLPort
        DB_USER                       = $MySQLUser
        DB_PASSWORD                   = $MySQLPassword
        DB_NAME                       = $MySQLDB
        LOG_DIR                       = $LOG_DIR
        ENABLE_SEED_DATA              = "false"
        REBUILD_EVENTS_ON_STARTUP     = "false"
        AUTO_INIT_DB_SCHEMA           = "0"
        API_HOST                      = "127.0.0.1"
        API_PORT                      = $AggregationPort
        REDIS_HOST                    = $RedisHost
        REDIS_PORT                    = $RedisPort
        REDIS_PASSWORD                = $RedisPassword
        REDIS_DB                      = "0"
        ENABLE_REDIS_COMMAND_CONSUMER = "1"
        AGGREGATION_COMMAND_STREAM    = "info_ai:aggregation:commands"
        AGGREGATION_COMMAND_CONSUMER_GROUP = "info_aggregation"
        AGGREGATION_RESULT_TTL_SECONDS    = "86400"
        EVENT_ANALYSIS_ENABLE_LLM     = "0"
        PYTHONUTF8="1"
    }

# ============================================================
# 2. info-serve
# ============================================================
Start-Bg -Name "info-serve" `
    -WorkDir (Join-Path $ROOT_DIR "info-serve") `
    -Command "go" `
    -Arguments "run ./cmd/server" `
    -EnvVars @{
        INFO_SERVE_HTTP_ADDR       = ":$InfoServePort"
        INFO_SERVE_MYSQL_DSN       = $MYSQL_DSN
        INFO_SERVE_SESSION_SECRET  = "info-serve-local-dev-session-secret"
        REDIS_ADDR                 = $REDIS_ADDR
        REDIS_PASSWORD             = $RedisPassword
        REDIS_DB                   = "0"
        AGGREGATION_COMMAND_STREAM = "info_ai:aggregation:commands"
        AGGREGATION_RESULT_PREFIX  = "info_ai:aggregation:results:"
        AGGREGATION_RESULT_WAIT_MS = "5000"
        AGGREGATION_HTTP_BASE_URL  = "http://127.0.0.1:$AggregationPort"
        AGGREGATION_LLM_TIMEOUT_MS = "240000"
        GOPATH                     = $GoPath
        GOCACHE                    = $GoCache
        GOMODCACHE                 = $GoModCache
        GOTOOLCHAIN                = "local"
        GOPROXY                    = "https://goproxy.cn,direct"
    }

# ============================================================
# 3. info-admin
# ============================================================
Start-Bg -Name "info-admin" `
    -WorkDir (Join-Path $ROOT_DIR "info-admin") `
    -Command $npmCmd `
    -Arguments "run dev -- --host 127.0.0.1 --port $InfoAdminPort" `
    -EnvVars @{ VITE_API_BASE_URL = "/api" }

# ============================================================
# 4. info-mvp
# ============================================================
Start-Bg -Name "info-mvp" `
    -WorkDir (Join-Path $ROOT_DIR "info-mvp") `
    -Command $npmCmd `
    -Arguments "run dev:h5 -- --host 127.0.0.1 --port $InfoMvpPort" `
    -EnvVars @{ VITE_API_BASE_URL = "/api" }

# ============================================================
# wait for healthy
# ============================================================
Write-Step "wait for services"

function Wait-Url([string]$Url, [string]$Name, [int]$MaxSec = 30) {
    for ($i = 1; $i -le $MaxSec; $i++) {
        try {
            Invoke-WebRequest -Uri $Url -TimeoutSec 2 -UseBasicParsing -ErrorAction Stop | Out-Null
            Write-Ok "$Name ready: $Url"
            return
        } catch { Start-Sleep -Seconds 1 }
    }
    Write-Warn "$Name not ready yet, check logs."
}

Wait-Url "http://127.0.0.1:$AggregationPort/health" "aggregation" 30
Wait-Url "http://127.0.0.1:$InfoServePort/health"   "info-serve"  30
Wait-Url "http://127.0.0.1:$InfoAdminPort/"          "admin"       15
Wait-Url "http://127.0.0.1:$InfoMvpPort/"            "mvp"         15

# ============================================================
# summary
# ============================================================
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan

if ($script:Failed.Count -gt 0) {
    Write-Host " Failed services:" -ForegroundColor Red
    foreach ($svc in $script:Failed) { Write-Host "  x $svc" -ForegroundColor Red }
}

Write-Host ""
Write-Host "  MySQL:       ${MySQLHost}:${MySQLPort}/${MySQLDB}"
Write-Host "  Redis:       ${RedisHost}:${RedisPort}"
Write-Host "  Aggregation: http://localhost:${AggregationPort}"
Write-Host "  API:         http://localhost:${InfoServePort}"
Write-Host "  Admin:       http://localhost:${InfoAdminPort}"
Write-Host "  H5:          http://localhost:${InfoMvpPort}"
Write-Host ""
Write-Host "  Logs:  $LOG_DIR"
Write-Host "  Stop:  .\scripts\stop-local.ps1"
Write-Host ""
Write-Host "  Health check:"
Write-Host "    http://localhost:${AggregationPort}/health"
Write-Host "    http://localhost:${InfoServePort}/health"
Write-Host "    http://localhost:${InfoAdminPort}/data-quality/report"
Write-Host "    http://localhost:${InfoMvpPort}"
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan

if ($script:Failed.Count -gt 0) { exit 1 }
