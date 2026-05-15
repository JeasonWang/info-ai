# 信息达人 3 周 AI 情报台产品开发计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 3 周内完成一个可验收的“AI 热点事件情报台”应用版本，打穿采集、分析、AI 增强、用户端情报体验和后台治理闭环。

**Architecture:** `info_aggregation` 继续作为采集与事件分析核心服务，负责高质量数据采集、事件聚合、展示质量、LLM 分析内核和治理工具；`info-serve` 作为业务 API 和管理动作编排层，对用户端和管理端提供稳定接口；`info-mvp` 聚焦可信热点情报体验；`info-admin` 聚焦 RuoYi 风格运营治理台。近期不横向堆功能，先打穿“真实完整数据 -> 可信事件分析 -> AI 情报判断 -> 用户端可读 -> 后台可治理”的核心闭环。

**Tech Stack:** Python + FastAPI + SQLAlchemy + pytest, Go + MySQL + go test, Vue3 + TypeScript + Vite, uni-app, MySQL, Redis, OpenAI Compatible LLM API.

---

## 0. 已确认约束

### 交付范围

- 3 周后交付 H5 + 微信小程序可验收版本。
- 核心信源先聚焦：微博、今日头条、知乎、小红书、路透、36氪。
- 大模型先统一走 OpenAI Compatible 接口，不为每家模型做复杂独立适配。
- 专业版本阶段只建设能力底座，不做完整付费、订阅、多租户和商业化闭环。

### 产品原则

- 不做普通热点聚合。
- 不做简单 AI 摘要工具。
- 不堆功能入口，优先建设核心能力。
- 用户端要像“可信热点情报台”，不是新闻流。
- 管理端要像“运营治理台”，不是数据库表查看器。

---

## 1. 三周总目标

3 周内打穿以下核心闭环：

```text
核心信源采集
  -> 详情补偿与质量评分
  -> 事件聚合与质量分层
  -> 本地规则 + 大模型事件分析
  -> 可信事件 / 观察中事件
  -> 用户端情报卡片和深度详情
  -> 后台质量治理和分析补偿
```

最终用户看到的不是“热榜”，而是：

- 今日最值得看的可信事件。
- 正在发酵但待核实的观察中线索。
- 每个事件的一句话判断、可信度、最新变化、为什么重要。
- 详情页中的核心事实、证据链、多源视角、风险提示和时间线。

后台运营人员能看到：

- 哪个渠道采集不完整。
- 哪些事件分析质量差。
- 哪些事件被展示质量门控拦截。
- 大模型是否稳定、是否频繁 fallback。
- 可以触发重抓、重建、质量刷新、分析补偿。

---

## 2. 目录与职责

### `info_aggregation`

核心职责：

- 多渠道采集。
- 详情补偿。
- 采集质量评分。
- 事件聚合。
- 展示质量评分。
- 本地规则事件分析。
- 大模型事件分析内核。
- 审计、回填、预演、治理工具。

重点文件：

- `info_aggregation/crawlers/`
- `info_aggregation/services/quality/`
- `info_aggregation/services/analysis/`
- `info_aggregation/services/event_analysis/`
- `info_aggregation/tools/`
- `info_aggregation/tests/`

### `info-serve`

核心职责：

- 用户端事件 API。
- 管理端 API。
- 登录鉴权。
- 管理动作编排。
- 代理 `info_aggregation` 治理动作。

重点文件：

- `info-serve/internal/events/`
- `info-serve/internal/repository/`
- `info-serve/internal/admin/`
- `info-serve/internal/transport/http/`

### `info-mvp`

核心职责：

- 用户端 H5 / 小程序。
- 可信事件信息流。
- 观察中事件。
- 今日重点。
- 情报详情页。

重点文件：

- `info-mvp/src/pages/home/home.vue`
- `info-mvp/src/components/EventList.vue`
- `info-mvp/src/pages/event-detail/event-detail.vue`
- `info-mvp/src/services/api.ts`
- `info-mvp/src/types/index.ts`

### `info-admin`

核心职责：

- RuoYi / Element 风格运营管理台。
- 渠道质量治理。
- 事件分析质量治理。
- 大模型配置与调用质量治理。
- 低质量内容和观察中事件治理。

重点文件：

- `info-admin/src/views/DataQualityView.vue`
- `info-admin/src/views/LLMModelsView.vue`
- `info-admin/src/services/adminApi.ts`
- `info-admin/src/types/admin.ts`
- `info-admin/src/styles/base.css`

---

## 3. 第 1 周：采集与事件分析内核稳定

**周目标:** 让数据更完整、事件更可信、分析链路更可控。

### Task 1.1 核心信源采集质量看板

**目标:** 对 6 个核心信源形成稳定质量指标，知道哪里采不完整、为什么不完整。

**Files:**

- Modify: `info_aggregation/tools/event_quality_audit.py`
- Modify: `info_aggregation/services/quality/channel_quality_report.py`
- Modify: `info-serve/internal/repository/admin_store.go`
- Modify: `info-admin/src/views/DataQualityView.vue`
- Modify: `info-admin/src/types/admin.ts`
- Test: `info_aggregation/tests/test_event_quality_audit.py`
- Test: `info_aggregation/tests/test_channel_quality_report.py`
- Test: `info_aggregation/tests/test_event_analysis_quality_report.py`

**Steps:**

- [x] 增加核心信源列表：`weibo,toutiao,zhihu,xiaohongshu,reuters,36kr`。
- [x] 为每个核心信源输出：总数、complete、partial、list_only、failed、pending、平均正文长度、可用率、失败原因 Top N。
- [x] 在后台渠道质量页增加“核心信源优先治理”表格。
- [x] 测试：核心信源缺失时返回空指标而不是报错。
- [x] 测试：有 complete / partial / failed 样本时统计正确。
- [x] 运行：`cd info_aggregation && ./.venv/bin/python -m pytest tests/test_channel_quality_report.py tests/test_event_quality_audit.py tests/test_event_analysis_quality_report.py -q`
- [x] 运行：`cd info-serve && env GOCACHE=/tmp/info-serve-go-build-cache go test ./...`
- [x] 运行：`cd info-admin && npm test -- --run && npm run build`

**完成记录（2026-05-13）:**

- `info_aggregation` 渠道质量报告新增 `core_sources`，并补齐 status 分桶字段。
- `event_quality_audit.py` 新增核心信源审计输出，缺失信源返回 0 指标。
- `info-serve` MySQL 管理聚合层同步输出 `core_sources`，避免后台绕过 aggregation 时字段缺失。
- `info-admin` 渠道质量页新增“核心信源优先治理”表格，采用 RuoYi 风格表格与进度条展示。

**验收标准:**

- 后台能看到 6 个核心信源质量指标。
- 每个核心信源能定位主要失败原因。
- 管理员能知道优先治理哪个渠道。

### Task 1.2 Reuters 详情补强

**目标:** Reuters 不再大量停留在 list_only，至少形成可用 partial 详情，后续再探索完整正文。

**Files:**

- Modify: `info_aggregation/crawlers/reuters.py`
- Modify: `info_aggregation/tools/backfill_reuters_sitemap_metadata.py`
- Test: `info_aggregation/tests/test_reuters_crawler_detail.py`

**Steps:**

- [x] 增强 sitemap 元数据解析：分类、发布时间、图片说明、股票代码、Reuters news code。
- [x] 复查 `resolve_detail()`，确保历史 sitemap 元数据可被回填识别。
- [x] 对 401 / 403 正文失败保留明确失败原因。
- [x] 增加测试：sitemap 元数据能让 Reuters 进入 `partial`。
- [x] 增加测试：正文不可访问时不会覆盖已有可用 metadata。
- [x] 运行：`cd info_aggregation && ./.venv/bin/python -m pytest tests/test_reuters_crawler_detail.py tests/test_detail_pipeline.py -q`
- [x] 在真实库小批量执行：`./.venv/bin/python tools/backfill_reuters_sitemap_metadata.py --limit 100 --pretty`

**完成记录（2026-05-14）:**

- Reuters 详情链路保留 `http_401_blocked/http_403_blocked/http_404_not_found` 等明确失败原因，后台可直接定位阻断类型。
- `detail_pipeline` 在 fallback 到列表内容时保留上一层失败原因和规则，不再全部压成 `detail_unavailable`。
- 小批量回填处理 43 条 Reuters sitemap metadata：15 条进入 `complete`，28 条进入 `partial`。

**验收标准:**

- Reuters `list_only` 数量继续下降。
- Reuters 数据至少能提供标题、时间、分类、来源 URL、结构化 metadata。
- 正文失败原因清晰可见。

### Task 1.3 事件聚合预演与错合并控制

**目标:** 真实重建前可预演，避免错合并污染用户端。

**Files:**

- Modify: `info_aggregation/tools/event_rebuild_preview.py`
- Modify: `info_aggregation/services/analysis/event_builder.py`
- Test: `info_aggregation/tests/test_event_api.py`

**Steps:**

- [x] 预演工具输出：候选事件组、单条组比例、多来源组比例、命中 existing event 状态。
- [x] 增加样本输出字段：anchor、渠道数、标题样本、匹配事件状态。
- [x] 保持无实体字段合并策略保守。
- [x] 增加测试：事故类跨源标题可以合并。
- [x] 增加测试：无关社交标题不能合并。
- [x] 运行：`cd info_aggregation && ./.venv/bin/python tools/event_rebuild_preview.py --limit 300 --pretty`
- [x] 运行：`cd info_aggregation && ENABLE_PUBLIC_API=1 ./.venv/bin/python -m pytest tests/test_event_rebuild_preview.py tests/test_event_api.py -q`

**完成记录（2026-05-14）:**

- 预演报告新增 `risk_groups`，用于暴露疑似错合并或单源重复堆积组。
- 根据真实库预演发现并修复技术类错合并：Android 入行、NFT 交易市场、Claude Code 自动化开发不再被合成一个事件。
- 当前 300 条真实库预演结果：候选组 219，单条组 195，占 89.04%；多来源组 0；风险组主要来自微博单源重复聚集。

**验收标准:**

- 预演能在真实库上安全运行，不写数据。
- 不再出现大量无关社交标题被合成一个事件。
- 错合并风险优先于合并率，策略保持可解释。

### Task 1.4 LLM 事件分析内核稳定

**目标:** 大模型只服务核心判断能力，失败不影响事件生成。

**Files:**

- Modify: `info_aggregation/services/event_analysis/prompt_builder.py`
- Modify: `info_aggregation/services/event_analysis/result_parser.py`
- Modify: `info_aggregation/services/event_analysis/llm_runner.py`
- Modify: `info_aggregation/services/event_analysis/pipeline.py`
- Test: `info_aggregation/tests/test_event_analysis_prompt_builder.py`
- Test: `info_aggregation/tests/test_event_analysis_llm_runner.py`
- Test: `info_aggregation/tests/test_llm_call_logging.py`

**Steps:**

- [x] 固定事件分析 Prompt contract。
- [x] 固定 JSON 输出 contract。
- [x] LLM Runner 统一处理：调用、重试、归一化、校验。
- [x] Pipeline 只处理：是否启用 LLM、配置选择、日志、fallback。
- [x] 校验失败条件包含：摘要过短、半截句、低价值、缺时间线、重复标题。
- [x] 测试 LLM 成功记录日志。
- [x] 测试 LLM 失败记录日志并 fallback。
- [x] 测试 LLM 输出不合格时 fallback。
- [x] 运行：`cd info_aggregation && ./.venv/bin/python -m pytest tests/test_event_analysis_prompt_builder.py tests/test_event_analysis_llm_runner.py tests/test_llm_call_logging.py tests/test_event_analysis_pipeline.py -q`

**阶段记录（2026-05-13 / 2026-05-14）:**

- Prompt contract 补充一句话总结硬约束：35-90 个中文字符、完整判断句、不能照抄标题、不能以连接词或未完成短语结尾。
- LLM Runner 校验新增半截句识别，拦截 `正在/因为/以及/将/向` 等明显未完成结尾，避免半截摘要进入事件结果。
- Pipeline 保持编排职责：配置选择、调用、成功/失败日志、规则 fallback；坏模型输出会记录失败日志并回退。
- 成功日志验证 request/response payload，失败日志验证 error 和坏模型 response payload。

**验收标准:**

- LLM 失败不阻塞事件重建。
- LLM 输出不合格不会进用户端。
- 调用日志包含 request、response、error。
- fallback 结果可追踪。

### 第 1 周验收

必须通过：

```bash
cd info_aggregation
ENABLE_PUBLIC_API=1 ./.venv/bin/python -m pytest -q

cd ../info-admin
npm test -- --run
npm run build
```

第 1 周结束应达到：

- 核心信源质量可观测。
- 事件聚合可安全预演。
- active / monitoring 分层稳定。
- LLM 分析内核清晰、可扩展、可 fallback。

**验收记录（2026-05-14）:**

- `ENABLE_PUBLIC_API=1 ./.venv/bin/python -m pytest -q`：247 passed。
- `npm test -- --run`：9 passed。
- `npm run build`：通过。

---

## 4. 第 2 周：用户端情报体验打磨

**周目标:** 让 `info-mvp` 从普通事件列表变成“可信热点情报台”。

### Task 2.1 首页情报台收敛

**目标:** 用户打开首页 5 秒内知道今天最值得看的事件。

**Files:**

- Modify: `info-mvp/src/pages/home/home.vue`
- Modify: `info-mvp/src/components/EventList.vue`
- Modify: `info-mvp/src/services/api.ts`
- Modify: `info-mvp/src/types/index.ts`

**Steps:**

- [x] 首页保留“可信事件 / 观察中”入口。
- [x] 首页保留“今日重点 / 重点观察”区，只展示前三条。
- [x] 事件卡片展示：判断标签、一句话判断、可信度、来源数、最新变化。
- [x] 观察中事件展示自然语言原因。
- [x] 卡片里不要直接暴露原始 reason code。
- [x] 卡片文字在移动端不能溢出。
- [x] 运行：`cd info-mvp && npm run verify:h5`
- [x] 运行：`cd info-mvp && npm run verify:mp-weixin`

**完成记录（2026-05-14）:**

- 首页品牌与分享标题收敛为“信息达人 AI 情报台”。
- 今日重点/重点观察补充可信度与来源数，事件卡片补充可信度、最新变化、来源数。
- `display_quality_reason` 从原始 code 映射为自然语言，观察中事件不再直接暴露内部 reason code。
- H5 本地服务 `curl` 冒烟返回 200；Playwright 未安装，未做截图级视觉校验。

**验收标准:**

- 首页第一屏像情报台，不像普通新闻流。
- 可信事件和观察中事件区分清楚。
- 用户能快速判断哪些事件值得点开。

### Task 2.2 详情页情报结构固定

**目标:** 详情页稳定回答“发生了什么、为什么重要、证据是什么、风险是什么”。

**Files:**

- Modify: `info-mvp/src/pages/event-detail/event-detail.vue`
- Modify: `info-mvp/src/types/index.ts`

**Steps:**

- [x] 详情首屏展示：标题、一句话判断、质量标签、状态判断。
- [x] 新增或保留“情报摘要”：核心事实、最新进展、为什么重要、风险提示。
- [x] 展示证据链：可用来源、弱来源、来源质量。
- [x] 展示多源视角和来源对比。
- [x] 展示时间线。
- [x] monitoring 事件明确提示“不宜直接当作事实”。
- [x] 降低重复区块，避免同一段摘要重复出现。
- [x] 运行：`cd info-mvp && npm run verify:h5`
- [x] 运行：`cd info-mvp && npm run verify:mp-weixin`

**完成记录（2026-05-14）:**

- 详情页首屏保留质量标签、状态判断和一句话判断；monitoring 明确提示“证据不足，不宜直接当作事实”。
- 情报摘要作为主结构承载核心事实、最新进展、为什么重要、风险提示。
- 当情报摘要存在时，不再重复展示同内容的“发生了什么/为什么重要/最新进展/风险提示”长段落。

**验收标准:**

- 用户不读原文也能理解事件。
- 来源、不确定性、风险都可见。
- 详情页明显比热搜页面更有判断价值。

### Task 2.3 观察中事件产品化

**目标:** 观察中不是垃圾桶，而是“待核实线索池”。

**Files:**

- Modify: `info-mvp/src/components/EventList.vue`
- Modify: `info-mvp/src/pages/event-detail/event-detail.vue`
- Modify: `info_aggregation/services/analysis/event_display_quality.py`
- Test: `info_aggregation/tests/test_event_display_quality.py`

**Steps:**

- [x] 将 reason code 映射为自然语言解释。
- [x] 对社交热度缺事实源展示“已有热度，等待媒体/官方事实源确认”。
- [x] 对单一弱来源展示“当前只有单一弱来源，建议观察”。
- [x] 对缺完整来源展示“来源信息不完整，结论需谨慎”。
- [x] 测试：纯社交热度进入 monitoring。
- [x] 测试：官方/媒体事实源可以转 active。
- [x] 运行：`cd info_aggregation && ./.venv/bin/python -m pytest tests/test_event_display_quality.py -q`
- [x] 运行：`cd info-mvp && npm run verify:h5 && npm run verify:mp-weixin`

**完成记录（2026-05-14）:**

- 观察中事件 reason code 已在首页卡片和详情页映射为用户可理解的解释。
- 社交热度缺事实源、单一弱来源、缺完整来源均有明确提示。
- 展示质量门控收紧：无完整来源默认进入 monitoring，避免不确定内容进入可信事件流。
- 媒体/官方事实源信号扩展，含新华社、央视、财联社、澎湃、路透/Reuters 等。

**验收标准:**

- 观察中事件对用户有解释价值。
- 主信息流不被低确定性内容污染。
- 用户理解为什么这条事件还不能下结论。

### 第 2 周验收

必须通过：

```bash
cd info-mvp
npm run verify:h5
npm run verify:mp-weixin
```

第 2 周结束应达到：

- 首页具备可信情报台气质。
- 详情页形成稳定情报结构。
- 观察中事件可解释。
- 普通用户能感知产品差异。

---

## 5. 第 3 周：后台治理、联调和发布验收

**周目标:** 系统可运营、可诊断、可验收、可发布。

### Task 3.1 后台治理台收敛

**目标:** 管理员可以快速定位采集、分析、展示和 LLM 问题。

**Files:**

- Modify: `info-admin/src/views/DataQualityView.vue`
- Modify: `info-admin/src/views/LLMModelsView.vue`
- Modify: `info-admin/src/types/admin.ts`
- Modify: `info-admin/src/services/adminApi.ts`
- Modify: `info-admin/src/styles/base.css`
- Modify: `info-serve/internal/repository/admin_store.go`
- Modify: `info-serve/internal/transport/http/admin_handler.go`
- Test: `info-admin/src/services/__tests__/adminApi.spec.ts`
- Test: `info-serve/internal/transport/http/router_admin_routes_test.go`

**Steps:**

- [x] 渠道质量表格展示核心信源采集完整率。
- [x] 事件分析质量表格展示缺失分析、低置信度、fallback。
- [x] 展示质量区展示 active / monitoring / blocked 分布。
- [x] LLM 模型页展示调用成功率、失败原因、熔断状态。
- [x] 治理动作保留：刷新质量、重抓详情、重建事件、分析补偿。
- [x] 运行：`cd info-admin && npm test -- --run && npm run build`
- [x] 运行：`cd info-serve && GOCACHE=/tmp/info-serve-go-build-cache go test ./...`

**完成记录（2026-05-14）:**

- 后台数据质量页已展示核心信源完整率、事件分析风险、展示质量分布和治理动作。
- LLM 模型页新增健康概览：可用模型、近百次成功率、熔断中数量。
- 每个模型新增成功率与熔断状态 badge；`info_aggregation` 与 `info-serve` 同步输出 `success_rate`。

**验收标准:**

- 管理员能知道哪个渠道差。
- 能知道哪些事件分析差。
- 能知道 LLM 是否稳定。
- 能触发治理动作。

### Task 3.2 全链路联调脚本与验收记录

**目标:** 从采集到展示形成可重复验收流程。

**Files:**

- Modify: `scripts/start-local.sh`
- Modify: `scripts/stop-local.sh`
- Modify: `docs/开发文档/2026-05-13-信息达人AI情报台改造验收记录.md`
- Create: `docs/开发文档/2026-05-信息达人3周版本验收清单.md`

**Steps:**

- [x] 启动四个服务。
- [x] 检查采集服务健康。
- [x] 检查业务 API 健康。
- [x] 触发核心渠道采集。
- [x] 执行详情补偿。
- [x] 执行事件重建预演。
- [x] 执行事件重建。
- [x] 执行展示质量回填。
- [x] 检查后台质量报告。
- [x] 检查用户端首页。
- [x] 检查事件详情页。
- [x] 记录真实数据样本和指标。

**阶段记录（2026-05-14）:**

- `scripts/start-local.sh` 默认开启 `ENABLE_PUBLIC_API=1`，等待 aggregation `/health`，并输出采集 API、业务 API、后台和用户端入口。
- `scripts/stop-local.sh` 可清理四个本地服务 PID 和默认端口残留。
- 新增 `docs/开发文档/2026-05-信息达人3周版本验收清单.md`，覆盖产品定位、数据采集、事件分析、LLM、后台治理、本地联调和发布前命令。
- `bash -n scripts/start-local.sh scripts/stop-local.sh` 通过。
- 真实触发核心渠道采集和事件重建属于写库动作，已放入验收清单，正式验收时按小批量方式执行并记录样本指标。
- 2026-05-15 已实际触发核心渠道采集、执行详情补偿检查、执行事件重建并生成最新验收快照，发布前验证全部通过：`info_aggregation` 269 passed，`info-serve` go test 通过，`info-admin` 测试与构建通过，`info-mvp` H5 和微信小程序构建通过。
- 2026-05-15 最终快照确认：业务服务和采集服务均健康，首页抽样疑似摘要问题保持 0，用户端事件总数 345，发布前四项验证全部通过，事件分析风险从 98 进一步收敛到 4，低置信度降为 0，模型回退降为 0。

**验收标准:**

- 联调流程可重复。
- 真实数据可展示。
- 质量问题可定位。

### Task 3.3 发布前全量验证

**目标:** 形成 3 周版本发布门槛。

**Files:**

- Modify: `README.md`
- Modify: `GITHUB_AUTOMATED_DEPLOYMENT.md`
- Modify: `docker-compose.yml`
- Modify: `docker-compose-mysql.yml`
- Modify: `deploy.sh`

**Steps:**

- [x] 更新 README 当前版本说明。
- [x] 更新部署说明。
- [x] 确认数据库迁移脚本顺序。
- [x] 确认 `.env.example` 包含必要变量。
- [x] 运行 Python 全量测试。
- [x] 运行 Go 全量测试。
- [x] 运行 admin 测试与构建。
- [x] 运行 mvp H5 和小程序构建。
- [x] 记录最终验收结果。

必须通过：

```bash
cd info_aggregation
ENABLE_PUBLIC_API=1 ./.venv/bin/python -m pytest -q

cd ../info-serve
GOCACHE=/tmp/info-serve-go-build-cache go test ./...

cd ../info-admin
npm test -- --run
npm run build

cd ../info-mvp
npm run verify:h5
npm run verify:mp-weixin
```

**验收标准:**

- 所有测试和构建通过。
- 文档完整。
- 可以部署。
- 可以用真实数据验收产品核心价值。

**完成记录（2026-05-14）:**

- README 补充当前 AI 情报台版本的发布前检查点：Python 测试需带 `ENABLE_PUBLIC_API=1`，已有生产库升级需按版本顺序执行增量迁移。
- `.env.example`、`docker-compose.yml`、`deploy.sh` 补齐 `ENABLE_PUBLIC_API`、LLM 重试/熔断变量、Redis 命令总线结果变量。
- `GITHUB_AUTOMATED_DEPLOYMENT.md` 修正生产架构：当前 compose 启动 Redis 和四个应用容器，MySQL 连接宿主机或独立数据库；补齐全新库初始化和已有库迁移顺序。
- 语法和配置校验：`bash -n deploy.sh scripts/start-local.sh scripts/stop-local.sh` 通过，`docker compose config` 通过。
- 发布前命令通过：`info_aggregation` 249 passed；`info-serve` 全量 Go 测试通过；`info-admin` 9 tests passed 且构建通过；`info-mvp` H5 和微信小程序构建通过。

---

## 6. 三周内不做的事情

为避免反复修改，以下内容本阶段不做：

- 不做完整付费订阅。
- 不做多租户。
- 不做复杂推荐算法。
- 不做 App 原生端。
- 不做大而全行业舆情平台。
- 不做复杂专题系统。
- 不做过早商业化后台。
- 不做花哨但不提升判断效率的 UI。
- 不为每个大模型厂商单独写复杂 provider。

---

## 7. 风险与控制

### 风险 1：采集完整性不足

控制方式：

- 先做核心信源质量指标。
- 对每个失败原因可见化。
- 允许 partial，但不能把低质量内容直接推入 active。

### 风险 2：事件错合并

控制方式：

- 重建前必须预演。
- 无实体字段合并保持保守。
- 错合并优先级高于合并率。

### 风险 3：大模型输出不稳定

控制方式：

- Prompt contract 固定。
- JSON 输出 contract 固定。
- Runner 统一校验。
- 失败或不合格自动 fallback。
- 后台可看失败原因。

### 风险 4：用户端又变成普通列表

控制方式：

- 首页第一屏必须是情报台。
- 卡片必须有判断，不只展示标题。
- 详情页必须先展示情报摘要和证据，而不是堆原文。

### 风险 5：后台做成复杂 BI

控制方式：

- 后台只做治理需要的表格和图形化指标。
- 不做复杂分析报表。
- 所有按钮必须对应明确治理动作。

---

## 8. 每周里程碑

### 第 1 周结束

- 核心信源质量可观测。
- Reuters partial 能力继续增强。
- 事件聚合预演可用。
- LLM 分析内核稳定。
- `info_aggregation` 全量测试通过。

### 第 2 周结束

- 用户端首页具备情报台形态。
- 详情页具备情报摘要、证据链、多源视角、风险提示。
- 观察中事件可解释。
- H5 和微信小程序构建通过。

### 第 3 周结束

- 后台治理台可用。
- 全链路联调通过。
- 真实数据可验收。
- README、验收文档、部署文档更新。
- 形成可发布版本。

---

## 9. 执行方式建议

推荐执行方式：**按周推进，每周末做一次真实数据验收**。

每个任务必须遵守：

- 先看现有代码和测试。
- 小步修改。
- 每个核心能力补测试。
- 不做与本周目标无关的功能。
- 不重构无关模块。
- 不为了 UI 丰富牺牲信息判断效率。

每周结束必须输出：

- 已完成事项。
- 真实数据指标。
- 失败/风险。
- 下一周优先级。
