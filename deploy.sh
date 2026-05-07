#!/usr/bin/env bash
set -euo pipefail

# 信息达人 Max - 一键部署脚本
# 用法：
#   ./deploy.sh prod local-build   # 在当前机器构建镜像并启动
#   ./deploy.sh prod image-tar     # 加载 CI 上传的 images/info-ai-images.tar.gz 后启动

ENV_NAME=${1:-prod}
DEPLOY_MODE=${2:-local-build}
COMPOSE_FILE=${COMPOSE_FILE:-docker-compose.yml}
IMAGE_TAR=${IMAGE_TAR:-images/info-ai-images.tar.gz}

echo "========================================"
echo "信息达人 Max 部署脚本（info-mvp 用户端，不部署 info-max）"
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

read_env_value() {
    local key="$1"
    if [ ! -f ".env" ]; then
        return
    fi
    awk -F= -v key="${key}" '$1 == key { print substr($0, index($0, "=") + 1); exit }' .env
}

create_env_file() {
    if [ -f ".env" ]; then
        return
    fi

    local session_secret
    local mysql_password
    local admin_password
    if ! command -v openssl >/dev/null 2>&1; then
        echo "错误: 生产环境首次部署需要 openssl 生成随机密钥，请先安装 openssl 或手动创建 .env。" >&2
        exit 1
    fi
    session_secret=$(openssl rand -hex 32)
    mysql_password=$(openssl rand -base64 24 | tr -d '\n')
    admin_password=$(openssl rand -base64 18 | tr -d '\n')

    cat > .env <<EOF
# 数据库配置
MYSQL_ROOT_PASSWORD=${mysql_password}
MYSQL_DATABASE=info-max
DB_TYPE=mysql
DB_USER=root
DB_PASSWORD=${mysql_password}
DB_NAME=info-max
LOG_LEVEL=INFO
ENABLE_SEED_DATA=false

# info-serve 配置
INFO_SERVE_MYSQL_DSN=root:${mysql_password}@tcp(mysql:3306)/info-max?charset=utf8mb4&parseTime=true&loc=Local
INFO_SERVE_SESSION_SECRET=${session_secret}
INFO_ADMIN_EMAIL=admin@info-daren.local
INFO_ADMIN_PASSWORD=${admin_password}

# 渠道凭据配置。
# 知乎渠道凭据。知乎高质量采集需要有效登录态；不配置时可运行，但知乎详情会降级。
ZHIHU_COOKIE=
ZHIHU_ZSE_93=
ZHIHU_ZSE_96=
# 微博渠道凭据。用于提升话题搜索、移动搜索和网页搜索详情抓取成功率。
WEIBO_COOKIE=
# 小红书渠道凭据。用于提升动态详情页和渲染兜底成功率。
XHS_COOKIE=

# 前端接口配置。
# 生产 Docker 默认同源 /api，经由前端容器 Nginx 代理到 info-serve。
VITE_API_BASE_URL=/api

# 部署完成后的提示地址。服务器部署请改成真实域名或公网 IP。
PUBLIC_SITE_URL=http://localhost:8082
PUBLIC_ADMIN_URL=http://localhost:8081
PUBLIC_API_URL=http://localhost:8085
PUBLIC_AGGREGATION_URL=http://127.0.0.1:18000
EOF

    echo "已创建 .env 文件并生成随机数据库密码、会话密钥和管理员初始密码。请妥善保存 .env。"
    echo "管理员账号: admin@info-daren.local"
    echo "管理员初始密码: ${admin_password}"
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

bootstrap_admin() {
    echo "[5/6] 初始化管理员账号..."
    local retries=12
    local attempt=1
    while [ "${attempt}" -le "${retries}" ]; do
        if ${COMPOSE_CMD} -f "${COMPOSE_FILE}" exec -T info-serve sh -c './create-admin -email "$INFO_ADMIN_EMAIL" -password "$INFO_ADMIN_PASSWORD"'; then
            return
        fi
        echo "  等待 info-serve 可用后重试管理员初始化 (${attempt}/${retries})..."
        attempt=$((attempt + 1))
        sleep 3
    done

    echo "错误: 管理员账号初始化失败，请查看日志: ${COMPOSE_CMD} -f ${COMPOSE_FILE} logs info-serve"
    exit 1
}

check_services() {
    echo "[6/6] 检查服务状态..."
    sleep 8

    local failed=0
    local containers=("info-aggregation" "info-serve" "info-mvp" "info-admin")
    local compose_services=("info-aggregation" "info-serve" "info-mvp" "info-admin")
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
bootstrap_admin
check_services

PUBLIC_SITE_URL_VALUE=$(read_env_value "PUBLIC_SITE_URL")
PUBLIC_ADMIN_URL_VALUE=$(read_env_value "PUBLIC_ADMIN_URL")
PUBLIC_API_URL_VALUE=$(read_env_value "PUBLIC_API_URL")
PUBLIC_AGGREGATION_URL_VALUE=$(read_env_value "PUBLIC_AGGREGATION_URL")

echo ""
echo "========================================"
echo "部署完成"
echo "用户端: ${PUBLIC_SITE_URL_VALUE:-http://localhost:8082}"
echo "管理后台: ${PUBLIC_ADMIN_URL_VALUE:-http://localhost:8081}"
echo "业务 API: ${PUBLIC_API_URL_VALUE:-http://localhost:8085}"
echo "采集 API: ${PUBLIC_AGGREGATION_URL_VALUE:-http://127.0.0.1:18000}"
echo "========================================"
