# 信息达人 info-ai

信息达人是一个面向热点事件的 **AI 情报台**。它不做普通热榜聚合，也不只是把新闻做摘要，而是把全网噪声压缩成可验证、可追踪、可决策的事件情报。

产品核心不是回答“现在什么火了”，而是回答：

- 这件事到底发生了什么？
- 哪些信息是真的、有来源？
- 各平台叙事有什么差异？
- 事件处于发酵、扩散、反转、降温还是长期议题阶段？
- 它和历史上的哪些事件有关？
- 用户是否需要继续关注？

一句话愿景：

> 把全网热点噪声压缩成可验证、可追踪、可决策的事件情报。

当前正式版本为 **v1.0.0 / AI 情报台上线候选版**。产品重点是建设三项核心能力：高质量数据采集、可信事件分析、大模型情报增强。

> `info-max` 已正式废弃，不再维护。用户端统一维护 `info-mvp`。

---

## 产品定位

### 不做什么

信息达人不做普通“热点聚合”。这条路已经有微博热搜、今日头条、知乎热榜等成熟产品，继续做相同形态只会陷入同质化竞争。

信息达人也不做简单“热点事件 AI 总结”。如果只是把多篇内容压缩成一段摘要，用户很难形成持续使用理由，也体现不出数据采集和事件分析的复合价值。

### 要做什么

信息达人要做的是 **热点事件的 AI 情报台**：

- 对普通用户：用最少时间看懂可信热点，减少被噪声和情绪带偏。
- 对深度用户：提供证据链、多源视角、事件时间线、争议和反转提示。
- 对专业用户：面向媒体、公关、投资、运营、研究人员，提供关键词监控、事件演变追踪、每日简报和风险预警。

核心差异：

| 产品类型 | 主要回答的问题 |
|---|---|
| 热搜榜 | 大家正在看什么？ |
| 新闻客户端 | 媒体报道了什么？ |
| 搜索引擎 | 能搜到什么？ |
| 信息达人 | 这件事是否可信、是否重要、是否值得继续关注？ |

### 产品三层形态

1. **普通用户端**
   - 简洁事件卡片，只展示可信热点。
   - 卡片重点是：一句话看懂、可信度、最新变化、为什么重要、是否建议继续关注。

2. **深度详情页**
   - 展示核心事实、证据链、多源视角、时间线、反转/争议提示。
   - 让用户觉得“比刷热搜省时间，还更靠谱”。

3. **专业版 / 订阅版**
   - 面向媒体、公关、投资、运营、研究人员。
   - 提供行业关键词监控、事件演变追踪、每日简报和风险预警。

---

## 项目组成

```text
info-ai/
  info_aggregation/      # Python 采集底座与事件分析服务
  info-serve/            # Go 业务 API、用户鉴权、管理代理服务
  info-admin/            # Vue3 管理后台
  info-mvp/              # uni-app 用户端，支持 H5/小程序/后续 App
  scripts/               # 本地一键启动/关闭脚本
  docs/                  # 正式文档和历史归档
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

### 1. 数据采集能力

- 支持微博、今日头条、知乎、小红书、掘金、CSDN、博客园、36氪、路透、体育等渠道。
- 支持列表采集、详情二次抓取、搜索补偿、Cookie 凭证接入。
- 支持渠道质量报告、详情补偿队列、低质量数据治理。
- 目标不是“抓得多”，而是抓得真实、完整、及时、有价值。

数据采集是一切能力的基础。没有稳定完整的来源，事件分析和大模型判断都会变成空中楼阁。

### 2. 事件分析能力

- 将多条来源内容聚合为热点事件。
- 生成一句话摘要、发生了什么、为什么重要、最新进展、来源对比、风险提示和时间线。
- 支持本地规则兜底分析。
- 支持展示质量评分，将事件分为可信事件、观察中事件和低质量事件。
- 支持证据链、多源视角、事件发展脉络等结构化分析。

事件分析的目标不是“把内容拼成一个事件”，而是把多而杂的信息整理成用户能判断的情报。

### 3. 大模型情报增强能力

大模型不是简单摘要工具，而是事件情报能力的增强层。

当前和未来的大模型任务包括：

- **事实归纳**：从多来源中提取共同事实、争议事实、未证实说法。
- **一句话判断**：生成更自然、更有判断力的事件摘要。
- **叙事差异分析**：识别不同平台的传播角度、情绪倾向和信息差。
- **事件阶段判断**：判断事件处于发酵、扩散、反转、降温还是长期议题阶段。
- **历史关联**：识别相似历史事件、同一主体历史争议和同类风险。
- **关注建议**：给出继续关注、暂时观察、低价值围观或高风险预警等建议。

本地规则负责稳定、可控、低成本；大模型负责归纳、判断、解释和表达。模型失败时必须记录日志、触发熔断，并回退到本地规则分析。

### 4. 用户端体验

- `info-mvp` 是唯一继续维护的用户端。
- 支持 H5、微信小程序，后续可扩展 App。
- 支持事件列表、筛选、搜索、详情页、登录注册、收藏和阅读历史。
- 当前重点形态是“可信热点情报台”，不是普通热点列表。
- 首页聚焦可信事件和重点观察，详情页聚焦情报摘要、证据链、多源视角和风险提示。

### 5. 管理端治理

- 管理采集渠道、采集任务、详情补偿、质量报告。
- 支持查看事件分析质量。
- 支持配置多个大模型：地址、密钥、模型、启用状态、每日调用上限和调用状态。
- 参照 RuoYi / Element 管理台风格，强调表格化、图形化、可治理。

---

## 产品路线

### 近期重点

近期不横向堆功能，优先打穿核心闭环：

1. 采集完整性：核心信源的正文、时间、来源、图片和元数据尽量完整。
2. 事件分析可信度：标题、一句话总结、事实经过、风险提示稳定可用。
3. 大模型分析内核：模型调用、Prompt、解析、校验、fallback 架构清楚。
4. 用户端情报体验：卡片能快速判断，详情能看清证据，观察中事件能解释不确定性。

### MVP 核心闭环

每个事件都要尽量回答六个问题：

1. 发生了什么？
2. 哪些是已确认事实？
3. 哪些还只是传言或平台情绪？
4. 各平台怎么看？
5. 当前处于什么阶段？
6. 用户是否需要继续关注？

### 长期方向

- 从“热点列表”升级为“事件情报系统”。
- 从“单事件分析”升级为“事件演变追踪”。
- 从“公共热点”扩展到“行业/品牌/人物/公司风险监控”。
- 从“用户主动查看”扩展到“每日简报、订阅监控和风险预警”。

---

## 本地开发

本地开发使用本机 MySQL `3306`，不启动 Docker MySQL。你需要先确保 MySQL 8 可用，然后执行首版单文件初始化脚本：

```bash
cd info-ai
mysql -uroot -proot1234 < info_aggregation/sql/mysql8_init.sql
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
REDIS_ADDR=127.0.0.1:6379
REDIS_HOST=127.0.0.1
REDIS_PORT=6379
REDIS_DB=0
AGGREGATION_COMMAND_STREAM=info_ai:aggregation:commands
VITE_API_BASE_URL=/api

ENABLE_PUBLIC_API=1
EVENT_ANALYSIS_LLM_RETRY_TIMES=2
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
ENABLE_PUBLIC_API=1 ./.venv/bin/python -m pytest -q
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

- [部署上线手册](docs/ops/部署上线手册.md)
- [GITHUB_AUTOMATED_DEPLOYMENT.md](GITHUB_AUTOMATED_DEPLOYMENT.md)
- [deploy.sh](deploy.sh)
- [docker-compose.yml](docker-compose.yml)

生产部署前必须确认：

- 数据库已执行 `info_aggregation/sql/mysql8_init.sql`，脚本会创建 `info-max` 并初始化必要基础数据。
- `.env.prod` 或服务器环境变量已配置。
- `info-serve` 默认端口为 `8085`。
- `info-admin` 和 `info-mvp` 的 `/api` 代理指向 `info-serve`。
- `info_aggregation` 的日志时区为 `Asia/Shanghai`。

---

## 文档入口

- [文档地图](docs/README.md)
- [产品说明](docs/product/产品说明.md)
- [页面与产品设计](docs/product/页面与产品设计.md)
- [系统架构总览](docs/architecture/系统架构总览.md)
- [部署上线手册](docs/ops/部署上线手册.md)
- [2026-05-15 上线验收报告](docs/release/2026-05-15上线验收报告.md)
- [info_aggregation 架构文档](info_aggregation/README.md)
- [info-serve README](info-serve/README.md)
- [info-admin README](info-admin/README.md)
- [info-mvp README](info-mvp/README.md)
- [历史归档](docs/archive/README.md)

---

## 开发原则

- 功能要精，不在多。优先建设核心能力，不为“看起来丰富”而堆入口。
- 数据采集是第一核心能力，必须真实、完整、及时、有价值。
- 事件分析是第二核心能力，必须避免简单截断，优先输出通顺、可解释、有证据的分析。
- 大模型只服务核心判断能力：摘要、事实校验、叙事差异、阶段判断、历史关联和关注建议。
- 用户端不做普通热榜，要始终围绕“可信热点情报台”设计。
- 管理端只做运营治理，不直接连接数据库。
- 用户端只维护 `info-mvp`。
- 数据库变更必须同步 `info_aggregation/sql/`，正式部署说明同步更新 `docs/ops/部署上线手册.md`。
- 不再新增数据库外键约束，跨表一致性由代码和索引维护。
- 新增能力要有测试，采集渠道优化要尽量使用真实线上数据验证。
