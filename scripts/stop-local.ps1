#Requires -Version 5.1
<#
.SYNOPSIS
    关闭信息达人本地四个开发服务
.DESCRIPTION
    按 PID 文件关闭对应进程，再按端口清理残留进程。
    不停止 MySQL，不操作 Docker。
    关闭顺序与启动顺序相反：H5 端 -> 管理端 -> Go 服务 -> 采集服务。
#>

$ErrorActionPreference = "Continue"

$ROOT_DIR = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$LOG_DIR  = Join-Path $ROOT_DIR "logs\local"
New-Item -ItemType Directory -Path $LOG_DIR -Force | Out-Null

$services = @("info-mvp", "info-admin", "info-serve", "info_aggregation")
$portSpecs = @(
    @{ Port = 5175; Name = "H5" },
    @{ Port = 5174; Name = "admin" },
    @{ Port = 8085; Name = "api" },
    @{ Port = 8000; Name = "agg" }
)

function Stop-ProcessTree {
    [CmdletBinding()]
    param([int]$ParentPid, [string]$Name)

    $alive = Get-Process -Id $ParentPid -ErrorAction SilentlyContinue
    if (-not $alive) {
        Write-Host "  $Name : PID $ParentPid not running." -ForegroundColor Gray
        return
    }

    Write-Host "  $Name : stopping PID $ParentPid ($($alive.ProcessName))" -ForegroundColor Yellow

    $children = Get-CimInstance Win32_Process | Where-Object { $_.ParentProcessId -eq $ParentPid }
    foreach ($child in $children) {
        Stop-Process -Id $child.ProcessId -Force -ErrorAction SilentlyContinue
    }

    Stop-Process -Id $ParentPid -Force -ErrorAction SilentlyContinue

    for ($i = 1; $i -le 10; $i++) {
        if (-not (Get-Process -Id $ParentPid -ErrorAction SilentlyContinue)) { return }
        Start-Sleep -Seconds 1
    }

    if (Get-Process -Id $ParentPid -ErrorAction SilentlyContinue) {
        Write-Host "  $Name : force kill PID $ParentPid" -ForegroundColor Red
        Stop-Process -Id $ParentPid -Force -ErrorAction SilentlyContinue
        foreach ($child in $children) {
            Stop-Process -Id $child.ProcessId -Force -ErrorAction SilentlyContinue
        }
    }
}

Write-Host ""
Write-Host "==> stop local services" -ForegroundColor Cyan
Write-Host ""

foreach ($name in $services) {
    $pidFile = Join-Path $LOG_DIR "$name.pid"
    if (-not (Test-Path $pidFile)) {
        Write-Host "  $name : no pid file, skip." -ForegroundColor Gray
        continue
    }

    $pidVal = (Get-Content $pidFile -Raw).Trim()
    if ([string]::IsNullOrWhiteSpace($pidVal)) {
        Remove-Item $pidFile -Force -ErrorAction SilentlyContinue
        Write-Host "  $name : empty pid file, cleaned." -ForegroundColor Gray
        continue
    }

    Stop-ProcessTree -ParentPid ([int]$pidVal) -Name $name
    Remove-Item $pidFile -Force -ErrorAction SilentlyContinue
}

Write-Host ""
Write-Host "==> cleanup port leftovers" -ForegroundColor Cyan

foreach ($spec in $portSpecs) {
    $conns = Get-NetTCPConnection -LocalPort $spec.Port -State Listen -ErrorAction SilentlyContinue
    if (-not $conns) {
        Write-Host "  $($spec.Name) : port $($spec.Port) free." -ForegroundColor Gray
        continue
    }

    $pids = $conns | Select-Object -ExpandProperty OwningProcess -Unique
    Write-Host "  $($spec.Name) : kill port $($spec.Port) PID: $($pids -join ', ')" -ForegroundColor Yellow
    foreach ($pidVal in $pids) {
        Stop-ProcessTree -ParentPid $pidVal -Name "$($spec.Name)"
    }
}

Write-Host ""
Write-Host "All local services stopped. MySQL untouched." -ForegroundColor Green
Write-Host ""
