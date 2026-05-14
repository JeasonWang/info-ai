# 信息达人 Max GitHub 自动化部署指南

本文档说明如何通过 GitHub Actions 将信息达人 Max 部署到远程服务器。当前生产用户端使用 `info-mvp`，不再部署 `info-max`。

## 1. 部署架构

生产环境会启动以下容器。当前 `docker-compose.yml` 启动 Redis 和四个应用容器，MySQL 默认连接宿主机或独立数据库，不在本 compose 中启动。

| 服务 | 说明 | 默认访问 |
| --- | --- | --- |
| `redis` | 命令总线与任务结果缓存 | 仅服务器本机 `127.0.0.1:16379` |
| `info-aggregation` | 数据采集底座 | 仅服务器本机 `127.0.0.1:18000` |
| `info-serve` | 业务 API | `服务器IP:8085` |
| `info-mvp` | 用户端 H5/PC 页面 | `服务器IP:8082` |
| `info-admin` | 后台管理系统 | `服务器IP:8081` |

`info-mvp` 和 `info-admin` 默认通过容器内 Nginx 将 `/api` 代理到 `info-serve:8085`，生产环境不依赖浏览器跨域。

## 2. 服务器准备

推荐使用 Ubuntu 22.04/24.04 或其他支持 Docker Compose v2 的 Linux 服务器。

```bash
sudo mkdir -p /opt/info-ai
sudo chown -R "$USER:$USER" /opt/info-ai

docker version
docker compose version
```

如果服务器未安装 Docker，请先安装 Docker Engine 和 Docker Compose v2。

## 3. GitHub Secrets 配置

进入 GitHub 仓库：

`Settings -> Secrets and variables -> Actions -> New repository secret`

必须配置：

| Secret | 说明 |
| --- | --- |
| `SERVER_HOST` | 服务器公网 IP 或域名 |
| `SERVER_USER` | SSH 登录用户 |
| `SERVER_SSH_KEY` | SSH 私钥内容 |
| `SERVER_DEPLOY_PATH` | 部署目录，推荐 `/opt/info-ai` |

可选配置：

| Variable | 默认值 | 说明 |
| --- | --- | --- |
| `VITE_API_BASE_URL` | `/api` | 前端统一 API 基地址，用户端和管理端都使用它 |

推荐保持默认值，让用户端和管理端都走同源 `/api` 代理。

## 4. 服务器 `.env` 配置

第一次部署前，建议先在服务器创建 `/opt/info-ai/.env`。当前 `docker-compose.yml` 不启动 MySQL 容器，四个应用容器默认连接容器主机上的 MySQL 3306，因此数据库账号密码必须和服务器本机 MySQL 保持一致。

手动创建示例：

```bash
cd /opt/info-ai
cat > .env <<'EOF'
DB_TYPE=mysql
DB_HOST=host.docker.internal
DB_PORT=3306
DB_USER=root
DB_PASSWORD=请替换为主机MySQL密码
DB_NAME=info-max
LOG_LEVEL=INFO
TZ=Asia/Shanghai
APP_TIMEZONE=Asia/Shanghai
CRAWLER_MAX_CONTENT_LENGTH=12000
ENABLE_PUBLIC_API=1
EVENT_ANALYSIS_MODE=hybrid
EVENT_ANALYSIS_ENABLE_LLM=0
EVENT_ANALYSIS_LLM_RETRY_TIMES=2
EVENT_ANALYSIS_LLM_FAILURE_THRESHOLD=3
EVENT_ANALYSIS_LLM_COOLDOWN_MINUTES=30
ENABLE_SEED_DATA=false

REDIS_PASSWORD=
REDIS_DB=0
ENABLE_REDIS_COMMAND_CONSUMER=1
AGGREGATION_COMMAND_STREAM=info_ai:aggregation:commands
AGGREGATION_COMMAND_CONSUMER_GROUP=info_aggregation
AGGREGATION_RESULT_PREFIX=info_ai:aggregation:results:
AGGREGATION_RESULT_WAIT_MS=5000
AGGREGATION_HTTP_BASE_URL=http://info-aggregation:8000
AGGREGATION_LLM_TIMEOUT_MS=240000

INFO_SERVE_MYSQL_DSN=root:请替换为主机MySQL密码@tcp(host.docker.internal:3306)/info-max?charset=utf8mb4&parseTime=true&loc=Local
INFO_SERVE_SESSION_SECRET=请替换为强随机字符串
INFO_ADMIN_EMAIL=admin@info-daren.local
INFO_ADMIN_PASSWORD=请替换为强密码

VITE_API_BASE_URL=/api

PUBLIC_SITE_URL=http://服务器IP:8082
PUBLIC_ADMIN_URL=http://服务器IP:8081
PUBLIC_API_URL=http://服务器IP:8085
PUBLIC_AGGREGATION_URL=http://127.0.0.1:18000
EOF
```

渠道 Cookie / ZSE 不再放服务器 `.env`。初始化脚本会在数据库 `channel.cookies` 和 `channel.extra_credentials` 中写入 `status=sample` 的格式样例，真实登录态请部署后进入管理后台“凭证管理”保存。

## 5. 自动部署流程

推送到 `main` 或 `master` 后，根目录 workflow 会自动执行：

1. 拉取代码。
2. 构建 `info-aggregation`、`info-serve`、`info-mvp`、`info-admin` 镜像。
3. 导出镜像包 `images/info-ai-images.tar.gz`。
4. 上传镜像包、`docker-compose.yml`、`deploy.sh`、`mysql_schema_pro.sql`、`mysql_migration_max.sql` 到服务器。
5. 在服务器执行：

```bash
./deploy.sh prod image-tar
```

也可以在 GitHub Actions 页面手动点击 `Deploy -> Run workflow` 触发部署。

## 6. 部署后验证

在服务器执行：

```bash
cd /opt/info-ai
docker compose ps
docker compose logs -f info-serve
docker compose logs -f info-aggregation
```

接口验证：

```bash
curl http://127.0.0.1:8085/health
curl http://127.0.0.1:18000/health
```

页面验证：

```text
用户端：http://服务器IP:8082
管理端：http://服务器IP:8081
业务 API：http://服务器IP:8085/health
```

`info-aggregation` 和 MySQL 默认只绑定服务器本机地址，不应该直接从公网访问。

## 7. 数据库初始化和迁移说明

数据库脚本分工：

```text
info_aggregation/sql/mysql_schema_pro.sql      创建数据库和完整表结构
info_aggregation/sql/mysql_migration_max.sql   初始化必要数据
```

如果是全新生产库，首次初始化时应按顺序执行：

```text
mysql_schema_pro.sql
mysql_migration_max.sql
```

如果是已有生产库升级，先备份数据库，再按版本顺序执行增量迁移：

```text
migration_v1.1.0_channel_credentials.sql
migration_v1.1.0_event_analysis_source.sql
migration_v1.2.0_event_evolution.sql
migration_v1.3.0_database_cleanup.sql
migration_v1.4.0_incremental_rebuild.sql
migration_v1.5.0_event_display_quality.sql
```

注意：

- 当前 compose 不创建 MySQL 容器，也不自动执行数据库迁移。
- 全新生产库需要先初始化表结构和必要数据，再启动应用。
- 已有生产库升级必须先备份，再手动执行增量迁移脚本。

备份示例：

```bash
mysqldump -h 127.0.0.1 -uroot -p info-max > backup-info-max.sql
```

## 8. 常用运维命令

查看状态：

```bash
docker compose ps
```

查看日志：

```bash
docker compose logs -f info-serve
docker compose logs -f info-aggregation
docker compose logs -f info-mvp
docker compose logs -f info-admin
```

重启服务：

```bash
docker compose restart info-serve
docker compose restart info-aggregation
```

停止全部服务：

```bash
docker compose down
```

不要随意删除 `redis_data` 和 `aggregation_data` volume；MySQL 数据不在当前 compose volume 中，按你的宿主机或独立数据库备份策略管理。

## 9. 生产安全建议

- 不要公网开放 MySQL 端口。
- 不要公网开放 `info-aggregation`，采集服务应只被 `info-serve` 内部调用。
- 后续正式域名部署时，建议只开放 `80/443`，用 Nginx、Caddy 或云厂商网关转发：
  - `https://你的域名` -> `info-mvp`
  - `https://admin.你的域名` -> `info-admin`
  - `/api` -> `info-serve:8085`
- `.env` 必须只保存在服务器，不提交仓库。
- `INFO_SERVE_SESSION_SECRET`、`MYSQL_ROOT_PASSWORD`、`INFO_ADMIN_PASSWORD` 必须使用强随机值。

## 10. 故障排查

部署失败时先看 GitHub Actions 日志，确认 SSH、scp、Docker build 是否成功。

服务器侧排查：

```bash
cd /opt/info-ai
docker compose ps
docker compose logs --tail=200 info-serve
docker compose logs --tail=200 info-aggregation
```

如果管理员账号初始化失败，通常是 `info-serve` 未连上 MySQL 或数据库表未初始化完成。先看：

```bash
docker compose logs --tail=200 info-serve
```

如果前端页面能打开但接口失败，优先检查：

- `info-mvp/nginx.conf` 和 `info-admin/nginx.conf` 的 `/api` 代理。
- `info-serve` 容器是否健康。
- 浏览器 Network 面板中 `/api/*` 请求是否返回 200。
