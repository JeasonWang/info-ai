#!/usr/bin/env bash
set -euo pipefail

# 信息达人 Pro - 一键部署脚本
# 用法：
#   ./deploy.sh prod local-build   # 在当前机器构建镜像并启动
#   ./deploy.sh prod image-tar     # 加载 CI 上传的 images/info-ai-images.tar.gz 后启动

ENV_NAME=${1:-prod}
DEPLOY_MODE=${2:-local-build}
COMPOSE_FILE=${COMPOSE_FILE:-docker-compose.yml}
IMAGE_TAR=${IMAGE_TAR:-images/info-ai-images.tar.gz}

echo "========================================"
echo "信息达人 Pro 部署脚本"
echo "环境: ${ENV_NAME}"
echo "模式: ${DEPLOY_MODE}"
echo "========================================"

resolve_compose_cmd() {
    if docker compose version >/dev/null 2>&1; then
        echo "docker compose"
        return
    fi
    if command -v docker-compose >/dev/null 2>&1; then
        echo "docker-compose"
        return
    fi
    echo "错误: 未找到 docker compose 或 docker-compose" >&2
    exit 1
}

create_env_file() {
    if [ -f ".env" ]; then
        return
    fi

    local session_secret
    if command -v openssl >/dev/null 2>&1; then
        session_secret=$(openssl rand -hex 32)
    else
        session_secret="please-change-this-secret-before-production"
    fi

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
INFO_SERVE_SESSION_SECRET=${session_secret}

# 浏览器访问 info-serve 的公开地址。
# 本机部署可用 http://127.0.0.1:8080，服务器部署请改成真实域名或公网 IP。
VITE_INFO_SERVE_BASE_URL=http://127.0.0.1:8080
EOF

    echo "已创建 .env 文件。首次部署会继续启动服务，生产环境请尽快检查数据库密码、会话密钥和前端 API 地址。"
}

check_runtime() {
    echo "[1/5] 检查 Docker 环境..."
    if ! command -v docker >/dev/null 2>&1; then
        echo "错误: 请先安装 Docker"
        exit 1
    fi
    COMPOSE_CMD=$(resolve_compose_cmd)
}

prepare_env() {
    echo "[2/5] 准备环境配置..."
    create_env_file
}

deploy_services() {
    echo "[3/5] 准备服务镜像..."
    case "${DEPLOY_MODE}" in
        local-build)
            ${COMPOSE_CMD} -f "${COMPOSE_FILE}" build
            ;;
        image-tar)
            if [ ! -f "${IMAGE_TAR}" ]; then
                echo "错误: 镜像包不存在: ${IMAGE_TAR}"
                exit 1
            fi
            gzip -dc "${IMAGE_TAR}" | docker load
            ;;
        *)
            echo "错误: 不支持的部署模式 ${DEPLOY_MODE}，可选 local-build 或 image-tar"
            exit 1
            ;;
    esac

    echo "[4/5] 启动服务..."
    ${COMPOSE_CMD} -f "${COMPOSE_FILE}" up -d --remove-orphans --no-build
}

check_services() {
    echo "[5/5] 检查服务状态..."
    sleep 8

    local failed=0
    local containers=("info-mysql" "info-aggregation" "info-serve" "info-max" "info-admin")
    local compose_services=("mysql" "info-aggregation" "info-serve" "info-max" "info-admin")
    for index in "${!containers[@]}"; do
        local svc="${containers[$index]}"
        local compose_svc="${compose_services[$index]}"
        local running
        running=$(docker inspect -f '{{.State.Running}}' "${svc}" 2>/dev/null || echo "false")
        if [ "${running}" = "true" ]; then
            echo "  ✓ ${svc} 运行中"
        else
            echo "  ✗ ${svc} 启动异常，请查看日志: ${COMPOSE_CMD} -f ${COMPOSE_FILE} logs ${compose_svc}"
            failed=1
        fi
    done

    if [ "${failed}" -ne 0 ]; then
        exit 1
    fi
}

check_runtime
prepare_env
deploy_services
check_services

echo ""
echo "========================================"
echo "部署完成"
echo "用户端:   http://localhost"
echo "管理后台: http://localhost:8081"
echo "采集 API: http://localhost:18000"
echo "业务 API: http://localhost:8080"
echo "========================================"
