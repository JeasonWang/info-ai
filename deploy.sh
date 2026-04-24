#!/usr/bin/env bash
set -euo pipefail

# 信息达人 - 一键部署脚本
# 用法: ./deploy.sh [prod|staging]

ENV=${1:-prod}
COMPOSE_FILE="docker-compose.yml"

echo "========================================"
echo "信息达人部署脚本 - 环境: $ENV"
echo "========================================"

# 检查 Docker
echo "[1/5] 检查 Docker 环境..."
if ! command -v docker &>/dev/null || ! command -v docker-compose &>/dev/null; then
    echo "错误: 请先安装 Docker 和 docker-compose"
    exit 1
fi

# 创建环境变量文件
echo "[2/5] 准备环境配置..."
if [ ! -f ".env" ]; then
    cat > .env <<EOF
# 数据库配置
MYSQL_ROOT_PASSWORD=root1234
MYSQL_DATABASE=info-max
DB_TYPE=mysql
DB_USER=root
DB_PASSWORD=root1234
DB_NAME=info-max
LOG_LEVEL=INFO

# info-serve 配置
INFO_SERVE_MYSQL_DSN=root:root1234@tcp(mysql:3306)/info-max?charset=utf8mb4&parseTime=true&loc=Local
INFO_SERVE_SESSION_SECRET=$(openssl rand -hex 32)

# 前端构建变量（指向 info-serve 地址）
VITE_INFO_SERVE_BASE_URL=http://127.0.0.1:8080
EOF
    echo "已创建 .env 文件，请按需修改后重新运行"
    exit 0
fi

# 拉取最新代码（如果在 git 仓库中）
echo "[3/5] 更新代码..."
if [ -d ".git" ]; then
    git pull origin $(git rev-parse --abbrev-ref HEAD)
fi

# 构建并启动
echo "[4/5] 构建并启动服务..."
docker-compose -f $COMPOSE_FILE pull 2>/dev/null || true
docker-compose -f $COMPOSE_FILE down
docker-compose -f $COMPOSE_FILE up --build -d

# 等待并检查状态
echo "[5/5] 检查服务状态..."
sleep 5

services=("mysql" "info-aggregation" "info-serve" "info-max" "info-admin")
for svc in "${services[@]}"; do
    if docker-compose ps | grep -q "$svc.*Up"; then
        echo "  ✓ $svc 运行中"
    else
        echo "  ✗ $svc 启动异常，请检查日志: docker-compose logs $svc"
    fi
done

echo ""
echo "========================================"
echo "部署完成！"
echo "用户端:   http://localhost"
echo "管理后台: http://localhost:8081"
echo "采集API:  http://localhost:8000"
echo "业务API:  http://localhost:8080"
echo "========================================"
