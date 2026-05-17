<#
.SYNOPSIS
    信息达人 info-ai 本地开发数据库一键初始化脚本

.DESCRIPTION
    在本地 MySQL 8 中初始化 info-max 数据库。
    执行 info_aggregation/sql/mysql8_init.sql 创建 27 张表并写入基础数据：
    - 6 个分类、12 个渠道、12 个采集任务
    - 默认管理员账号 admin@info-daren.local / Admin123456
    - 2 条 LLM 模型配置（默认关闭）

.NOTES
    前置条件：MySQL 8 已安装并运行。
    脚本会自动创建 info-max 数据库（如果不存在）。
    脚本是幂等的：CREATE TABLE IF NOT EXISTS + ON DUPLICATE KEY UPDATE，可安全重复执行。

.EXAMPLE
    # 交互式输入密码
    .\scripts\init-db-local.ps1

    # 命令行传入密码
    .\scripts\init-db-local.ps1 -MySQLPassword 123456
#>

param(
    [string]$MySQLUser = "root",
    [string]$MySQLPassword = "",
    [string]$MySQLHost = "127.0.0.1",
    [string]$MySQLPort = "3306",
    [string]$Database = "info-max"
)

$ErrorActionPreference = "Stop"

# --- 定位 mysql.exe ---
$MySQLExe = $null
$candidates = @(
    "C:\Program Files\MySQL\MySQL Server 8.0\bin\mysql.exe",
    "C:\Program Files\MySQL\MySQL Server 8.4\bin\mysql.exe",
    "C:\Program Files\MySQL\MySQL Server 9.0\bin\mysql.exe"
)

foreach ($path in $candidates) {
    if (Test-Path $path) {
        $MySQLExe = $path
        break
    }
}

if (-not $MySQLExe) {
    $found = Get-Command mysql -ErrorAction SilentlyContinue
    if ($found) {
        $MySQLExe = $found.Source
    }
}

if (-not $MySQLExe) {
    Write-Error "找不到 mysql.exe，请确认 MySQL 8 已安装或手动指定路径。"
    exit 1
}

Write-Host "[信息] 使用 MySQL 客户端: $MySQLExe" -ForegroundColor Cyan

# --- 密码输入 ---
if (-not $MySQLPassword) {
    $securePwd = Read-Host "请输入 MySQL $MySQLUser 用户密码" -AsSecureString
    $MySQLPassword = [System.Runtime.InteropServices.Marshal]::PtrToStringAuto(
        [System.Runtime.InteropServices.Marshal]::SecureStringToBSTR($securePwd)
    )
}

# --- 检查连接 ---
Write-Host "[检查] 测试 MySQL 连接..." -ForegroundColor Yellow
$testResult = & $MySQLExe -h $MySQLHost -P $MySQLPort -u $MySQLUser -p"$MySQLPassword" -e "SELECT 1 AS ok" 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Error "MySQL 连接失败，请检查用户名和密码。"
    Write-Error ($testResult | Where-Object { $_ -notmatch 'Warning' } | Out-String)
    exit 1
}
Write-Host "[检查] 连接成功" -ForegroundColor Green

# --- 检查/创建数据库 ---
Write-Host "[检查] 确认数据库 $Database 存在..." -ForegroundColor Yellow
& $MySQLExe -h $MySQLHost -P $MySQLPort -u $MySQLUser -p"$MySQLPassword" -e "CREATE DATABASE IF NOT EXISTS ``$Database`` DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;" 2>&1 | Out-Null
Write-Host "[检查] 数据库 $Database 已就绪" -ForegroundColor Green

# --- 执行初始化 SQL ---
$sqlFile = Join-Path $PSScriptRoot "..\info_aggregation\sql\mysql8_init.sql"
$sqlFile = [System.IO.Path]::GetFullPath($sqlFile)

if (-not (Test-Path $sqlFile)) {
    Write-Error "找不到初始化 SQL 文件: $sqlFile"
    exit 1
}

Write-Host "[执行] 初始化数据库: $sqlFile" -ForegroundColor Yellow
# 使用 cmd.exe type 管道传输，避免 PowerShell UTF-8 编码导致中文 COMMENT 乱码
$initOutput = cmd /c "type `"$sqlFile`" | `"$MySQLExe`" -h $MySQLHost -P $MySQLPort -u $MySQLUser -p$MySQLPassword" 2>&1

if ($LASTEXITCODE -ne 0 -and ($initOutput | Where-Object { $_ -match 'ERROR' })) {
    Write-Error "初始化失败："
    Write-Error ($initOutput | Where-Object { $_ -match 'ERROR' } | Out-String)
    exit 1
}

# --- 输出验证结果 ---
Write-Host ""
Write-Host "[完成] 数据库初始化结果：" -ForegroundColor Green
$initOutput | Where-Object { $_ -notmatch 'Warning' -and $_ -match '\S' } | ForEach-Object {
    Write-Host "  $_" -ForegroundColor White
}

# --- 统计 ---
Write-Host ""
Write-Host "[统计] 各表行数：" -ForegroundColor Cyan
$tableCount = & $MySQLExe -h $MySQLHost -P $MySQLPort -u $MySQLUser -p"$MySQLPassword" -e "USE ``$Database``; SELECT table_name, table_rows FROM information_schema.tables WHERE table_schema = '$Database' AND table_rows > 0 ORDER BY table_name;" 2>&1 | Where-Object { $_ -notmatch 'Warning' }
$tableCount | ForEach-Object { Write-Host "  $_" -ForegroundColor White }

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host " 数据库初始化完成" -ForegroundColor Green
Write-Host " 数据库: $Database" -ForegroundColor White
Write-Host " 管理员: admin@info-daren.local" -ForegroundColor White
Write-Host " 默认密码: Admin123456 (首次登录后请修改)" -ForegroundColor Yellow
Write-Host "========================================" -ForegroundColor Cyan
