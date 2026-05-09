# 信息达人 info-ai

信息达人是一个热点事件采集、分析和展示系统。当前正式版本为 **v1.0.0 / max 线上版**，产品重点是采集完整、有价值的数据，并把多渠道内容加工成用户能理解的热点事件分析。

> `info-max` 已正式废弃，不再维护。用户端统一维护 `info-mvp`。

---

## 项目组成

```text
info-ai/
  info_aggregation/      # Python 采集底座与事件分析服务
  info-serve/            # Go 业务 API、用户鉴权、管理代理服务
  info-admin/            # Vue3 管理后台
  info-mvp/              # uni-app 用户端，支持 H5/小程序/后续 App
  scripts/               # 本地一键启动/关闭脚本
  docs/                  # 开发文档、数据库脚本、评审记录
  docker-compose.yml     # 生产容器编排，不包含 MySQL 的部署方式可单独调整
  deploy.sh              # 自动化部署入口
```

### 服务边界

| 服务 | 技术栈 | 默认端口 | 职责 |
|------|--------|----------|------|
| `info_aggregation` | Python + FastAPI + SQLAlchemy + APScheduler | `8000` | 多渠道采集、详情补偿、数据质量、事件分析、大模型熔断 |
| `info-serve` | Go | `8085` | 用户端 API、管理端 API、登录鉴权、审计、代理采集管理动作 |
| `info-admin` | Vue3 + TypeScript + Vite | `5174` | 管理后台、采集监控、质量治理、模型配置 |
| `info-mvp` | uni-app + Vue3 + TypeScript | `5175` | 用户端 H5/小程序，展示热点事件和详情分析 |

---

## 核心能力

### 数据采集

- 支持微博、今日头条、知乎、小红书、掘金、CSDN、博客园、36氪、路透、体育等渠道。
- 支持列表采集、详情二次抓取、搜索补偿、Cookie 凭证接入。
- 支持渠道质量报告、详情补偿队列、低质量数据治理。

### 事件分析

- 将多条来源内容聚合为热点事件。
- 生成一句话摘要、发生了什么、为什么重要、最新进展、来源对比、风险提示和时间线。
- 支持本地规则兜底分析。
- 支持管理端配置多个 OpenAI Compatible 大模型，例如本地千问、DeepSeek 等。
- 大模型失败后自动记录日志、熔断，并回退本地规则分析。

### 用户端

- `info-mvp` 是唯一继续维护的用户端。
- 支持 H5、微信小程序，后续可扩展 App。
- 支持事件列表、筛选、搜索、详情页、登录注册、收藏和阅读历史。

### 管理端

- 管理采集渠道、采集任务、详情补偿、质量报告。
- 支持查看事件分析质量。
- 支持配置多个大模型：地址、密钥、模型、启用状态、每日调用上限和调用状态。

---

## 本地开发

本地开发使用本机 MySQL `3306`，不启动 Docker MySQL。你需要先确保 MySQL 可用，并已创建数据库：

```sql
CREATE DATABASE IF NOT EXISTS `info-max` DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

初始化数据库：

```bash
cd info-ai
mysql -uroot -proot1234 info-max < info_aggregation/sql/mysql_schema_pro.sql
mysql -uroot -proot1234 info-max < info_aggregation/sql/mysql_migration_max.sql
```

一键启动四个本地服务：

```bash
cd info-ai
./scripts/start-local.sh
```

默认地址：

| 服务 | 地址 |
|------|------|
| 采集 API | [http://localhost:8000](http://localhost:8000) |
| 业务 API | [http://localhost:8085](http://localhost:8085) |
| 管理后台 | [http://localhost:5174](http://localhost:5174) |
| 用户端 H5 | [http://localhost:5175](http://localhost:5175) |

关闭服务：

```bash
./scripts/stop-local.sh
```

本地日志目录：

```text
logs/local/
```

---

## 环境变量

根目录 `.env.example` 提供主要变量模板。生产部署时不要提交真实 `.env`，应由服务器环境变量、GitHub Secrets 或部署脚本生成。

常用变量：

```text
MYSQL_HOST=127.0.0.1
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=root1234
MYSQL_DB=info-max

INFO_SERVE_HTTP_ADDR=:8085
INFO_AGGREGATION_BASE_URL=http://info-aggregation:8000
VITE_API_BASE_URL=/api

EVENT_ANALYSIS_LLM_FAILURE_THRESHOLD=3
EVENT_ANALYSIS_LLM_COOLDOWN_MINUTES=30
```

前端统一使用：

```text
VITE_API_BASE_URL
```

`VITE_INFO_SERVE_BASE_URL` 已废弃，不再新增使用。

---

## 测试与构建

### info_aggregation

```bash
cd info_aggregation
./.venv/bin/python -m pytest -q
```

### info-serve

```bash
cd info-serve
GOCACHE=/tmp/info-serve-go-build-cache go test ./...
```

### info-admin

```bash
cd info-admin
npm test -- --run
npm run build
```

### info-mvp

```bash
cd info-mvp
npm run verify:h5
npm run verify:mp-weixin
```

---

## 部署

当前推荐方式：

1. 代码推送到 GitHub。
2. GitHub Actions 触发部署。
3. 远程服务器执行 `deploy.sh`。
4. 容器化部署 `info_aggregation`、`info-serve`、`info-admin`、`info-mvp`。
5. MySQL 可选择容器化或连接宿主机/独立数据库。

自动化部署说明见：

- [GITHUB_AUTOMATED_DEPLOYMENT.md](GITHUB_AUTOMATED_DEPLOYMENT.md)
- [deploy.sh](deploy.sh)
- [docker-compose.yml](docker-compose.yml)

生产部署前必须确认：

- 数据库脚本已执行。
- `.env.prod` 或服务器环境变量已配置。
- `info-serve` 默认端口为 `8085`。
- `info-admin` 和 `info-mvp` 的 `/api` 代理指向 `info-serve`。
- `info_aggregation` 的日志时区为 `Asia/Shanghai`。

---

## 文档入口

- [info_aggregation 架构文档](info_aggregation/README.md)
- [info-serve README](info-serve/README.md)
- [info-admin README](info-admin/README.md)
- [info-mvp README](info-mvp/README.md)
- [开发文档](docs/开发文档)
- [数据库脚本](docs/数据库)

---

## 开发原则

- 数据采集是第一核心能力，优先保证真实、完整、及时、有价值。
- 事件分析是第二核心能力，必须避免简单截断，优先输出通顺、可解释、有证据的分析。
- 管理端只做运营治理，不直接连接数据库。
- 用户端只维护 `info-mvp`。
- 数据库变更必须同步 `info_aggregation/sql/` 和必要的 `docs/数据库/` 增量脚本。
- 不再新增数据库外键约束，跨表一致性由代码和索引维护。
- 新增能力要有测试，采集渠道优化要尽量使用真实线上数据验证。
