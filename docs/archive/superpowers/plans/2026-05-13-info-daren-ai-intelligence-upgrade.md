# Info Daren AI Intelligence Upgrade Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把信息达人从普通热点聚合升级为“热点事件的 AI 情报台”，优先解决采集不完整、事件分析低价值、LLM 使用不稳定和用户端展示噪声过多的问题。

**Architecture:** 改造按“采集质量门槛 -> 事件分析质量门槛 -> LLM 增强与审计 -> 用户端可信情报形态”推进。`info_aggregation` 继续作为数据与分析核心，`info-serve` 负责对外 API 和展示过滤，`info-admin` 承接质量治理与模型运维，`info-mvp` 只展示足够可信、有价值的事件情报。

**Tech Stack:** Python, FastAPI, SQLAlchemy, MySQL, pytest, Go, Vue3, uni-app, TypeScript, OpenAI-compatible LLM API

---

## 1. 产品大方向

信息达人不再以“全网热点列表”作为核心卖点，而是定位为：

> 把全网噪声压缩成可验证、可追踪、可决策的事件情报。

用户打开产品时，不应该只是看到“什么上热榜了”，而应该快速知道：

- 这件事到底发生了什么。
- 信息来自哪些渠道，哪些来源可信，哪些来源只是热度信号。
- 事件处于发酵、扩散、反转、降温还是已解决阶段。
- 这件事为什么重要，是否值得继续关注。
- 和历史上、同实体、同主题的事件有什么联系。

## 2. 当前诊断基线

本计划基于 2026-05-13 本地库和代码审查结论：

- active 事件约 1708 条，其中 `one_line_summary` 少于 12 字的约 1025 条。
- 小红书和微博平均正文长度分别约 138 字、127 字，热点/社交渠道列表态数据大量进入事件展示。
- Reuters 当前大量来自 sitemap 元数据，467 条里约 436 条是 `list_only`。
- 热点分类 1365 个 active 事件中约 1249 个是单来源事件。
- LLM 有接入、配置、调用日志和熔断，但事件分析运行中大多数仍是规则分析；最近主模型存在 DNS 失败和超时熔断。
- 标题在 crawler 和 cleaner 层大量 `[:40]` 截断，英文标题尤其容易变成半截话。

## 3. 总体阶段

### Phase 0: 质量基线与回归样本

目标：先把“坏在哪里”量化，避免改造只凭体感。

交付：

- 采集质量基线报告：按渠道统计 `complete/partial/list_only/failed/pending`、平均正文长度、可用来源比例。
- 事件展示质量报告：统计短摘要、低价值摘要、单来源事件、规则/LLM 占比、LLM 失败原因。
- 固化 20-30 个真实坏样本，作为后续回归测试样本。

验收：

- 能一键输出质量报告。
- 报告能指出每个渠道最主要的问题。
- 后续每次改造前后能对比“坏摘要数量”和“可展示事件比例”。

### Phase 1: 采集质量和详情补偿闭环

目标：让 `info_aggregation` 区分“热度信号”和“可分析事实来源”，不再把列表摘要直接当完整正文。

交付：

- 放宽标题存储长度，移除 crawler/cleaner 层的 40 字硬截断，保留数据库 200 字上限。
- 新增低价值内容识别规则：过滤 `互动：点赞`、`hot/new`、`热榜分类`、作者名、纯表情、纯编号、纯榜单元数据。
- 针对微博、小红书、Reuters 拆分质量策略：
  - 微博、小红书默认作为热度信号，只有详情补偿成功或多来源交叉时才可进入用户端事件。
  - Reuters sitemap 元数据保留为线索，不作为完整国际事件正文。
  - 文章型渠道继续作为高价值事实来源。
- 详情补偿队列增加优先级策略：优先处理已进入高热度候选事件但来源弱的 Info。

验收：

- 新增数据中不再出现 `hot。`、`new。`、`互动：点赞xx。` 作为事件一句话摘要。
- 标题不再因为 40 字截断产生英文半句。
- 热点/社交来源的弱数据仍可保留在库中，但默认不能直接成为用户端可信事件。

### Phase 2: 事件可展示门槛

目标：建立“采集到了”和“值得展示给用户”之间的硬门槛。

交付：

- 为事件引入展示质量字段：`display_quality_score`、`display_quality_reason`、`display_quality_level`。
- 引入事件展示状态：
  - `active`: 可展示，满足来源数量、正文完整度、分析质量要求。
  - `monitoring`: 仅管理端/内部可见，代表正在观察的热度信号。
  - `low_quality`: 低质量，不进入用户端列表。
- 事件入库和重建时应用门槛：
  - 单来源且详情弱：默认 `monitoring`。
  - 多来源但全是弱来源：默认 `monitoring`。
  - 至少一个完整事实来源，或两个以上可用来源交叉验证：可进入 `active`。
- `info-serve` 列表接口只返回 `active`，管理端可查看全部状态。

验收：

- 用户端首页 active 事件数量可能减少，但摘要质量明显提升。
- 单来源小红书生活笔记、纯微博热榜元数据不再占据首页。
- 管理端仍能看到被拦截的 monitoring/low_quality 事件及原因。

### Phase 3: 本地规则分析升级

目标：即使 LLM 不可用，也能生成稳定、完整、有证据的基础分析。

交付：

- 规则分析输入只使用 `analysis_ready_items`，并禁止低价值文本参与摘要生成。
- `one_line_summary` 生成策略改造：
  - 不能直接取正文第一句。
  - 不能只输出热度、点赞、分类、作者、榜单字段。
  - 对单来源弱事实输出“线索态”摘要，避免伪装成确定事件。
- `what_happened`、`latest_update`、`why_it_matters` 增加证据依赖：
  - 没有事实证据时明确提示“当前仍是热度线索”。
  - 有多个来源时才输出来源对比和扩散判断。
- validator 扩展质量规则：
  - 低价值模式检测。
  - 标题复读检测。
  - 断句/省略号/半截英文检测。
  - 摘要与输入事实支撑关系检测。

验收：

- LLM 关闭时，事件详情仍能输出通顺且不误导的基础分析。
- 弱来源事件不会生成过度肯定的结论。
- 规则分析的质量分能反映真实来源完整度。

### Phase 4: LLM 增强正确使用

目标：让大模型成为“高质量事件分析增强器”，不是低质量输入的润色器。

交付：

- LLM 输入门槛：
  - 只传入完整或可用来源。
  - 每条来源附带质量分、风险原因、来源 URL、时间和渠道。
  - 弱来源只作为“热度线索”上下文，不作为事实依据。
- LLM Prompt 重构：
  - 输出必须区分“已证实事实”“仍待验证线索”“多渠道差异”“最新变化”。
  - 禁止编造没有来源支撑的事实。
  - 要求每个关键结论能回指来源序号。
- LLM 输出结构升级：
  - 保留现有字段兼容前端。
  - 增加 `claims`、`evidence_refs`、`uncertainty_flags`、`source_quality_notes` 等内部结构。
- LLM 失败策略升级：
  - 当前模型失败后尝试下一个可用模型。
  - 超时、DNS、JSON 解析失败分别记录原因。
  - 熔断后管理端明确展示“当前使用规则兜底”。
- LLM 审计日志完整化：
  - 事件分析调用也记录 prompt、response、解析失败内容和选用来源摘要。
  - 管理端能抽检最近调用。

验收：

- LLM 成功时，摘要必须比规则版更具解释性，而不是只改写标题。
- LLM 失败时不影响事件重建，不产生半截摘要。
- 管理端能定位某个坏摘要对应的 prompt、模型响应、来源质量。

### Phase 5: info-mvp 用户产品形态升级

目标：把用户端从“事件列表”变成“可信热点情报流”。

交付：

- 首页卡片重构：
  - 第一视觉：事件标题、可信一句话、阶段标签、可信度。
  - 次要信息：来源数、最新更新时间、热度趋势。
  - 不展示低价值 monitoring 事件。
- 详情页重构为情报页：
  - `发生了什么`
  - `为什么重要`
  - `最新变化`
  - `证据链`
  - `多源视角`
  - `风险与待验证`
  - `发展脉络`
- 增加“继续关注”产品动作：
  - 收藏事件。
  - 对同实体/同主题新进展给出提示。
  - 后续可接订阅消息或每日简报。

验收：

- 用户端首屏不再被低价值单条内容占满。
- 用户能在详情页看出“结论从哪里来”。
- 弱事实事件不会以确定口吻误导用户。

### Phase 6: info-admin 运营治理台

目标：让运营和开发能持续发现、修复和验证数据质量问题。

交付：

- 采集质量看板：
  - 渠道详情完整率。
  - pending/failed/list_only backlog。
  - 最近 24 小时质量趋势。
- 事件分析质量看板：
  - 短摘要、低价值摘要、单来源 active、LLM fallback、熔断模型。
  - 支持一键加入详情补偿、一键重新分析。
- LLM 模型运维：
  - 模型健康状态。
  - 日调用量、成功率、平均耗时、失败原因分布。
  - prompt/response 抽检入口。

验收：

- 管理端能解释“为什么这个事件没展示”。
- 能从坏事件反向创建补偿任务并重建分析。
- 能及时发现模型熔断或质量下降。

## 4. 详细实施任务

### Task 1: 建立质量基线审计工具

**Files:**

- Create: `info_aggregation/tools/event_quality_audit.py`
- Test: `info_aggregation/tests/test_event_quality_audit.py`
- Docs: `docs/开发文档/2026-05-13-信息达人AI情报台改造验收记录.md`

- [ ] Step 1: 新增审计函数，统计渠道详情质量、事件摘要质量、LLM 调用质量。
- [ ] Step 2: 测试短摘要、低价值摘要、单来源 active、LLM fallback 统计。
- [ ] Step 3: 增加命令行输出 JSON，便于改造前后对比。
- [ ] Step 4: 在验收记录中保存首次基线结果。

### Task 2: 修正标题截断和低价值内容识别

**Files:**

- Modify: `info_aggregation/cleaners/__init__.py`
- Modify: `info_aggregation/crawlers/weibo.py`
- Modify: `info_aggregation/crawlers/xiaohongshu.py`
- Modify: `info_aggregation/crawlers/reuters.py`
- Modify: `info_aggregation/crawlers/toutiao.py`
- Modify: `info_aggregation/crawlers/zhihu.py`
- Modify: `info_aggregation/crawlers/csdn.py`
- Modify: `info_aggregation/crawlers/juejin.py`
- Modify: `info_aggregation/crawlers/kr36.py`
- Modify: `info_aggregation/services/quality/data_quality.py`
- Test: `info_aggregation/tests/test_data_quality_gate.py`
- Test: `info_aggregation/tests/test_reuters_crawler_detail.py`
- Test: `info_aggregation/tests/test_weibo_crawler_detail.py`
- Test: `info_aggregation/tests/test_xiaohongshu_crawler_detail.py`

- [ ] Step 1: 把标题清洗上限从 40 放宽到 200，crawler 不再提前截到 40。
- [ ] Step 2: 增加低价值摘要模式：互动计数、榜单标签、作者名、纯表情、纯编号、`hot/new`。
- [ ] Step 3: Reuters sitemap 内容标记为线索元数据，不标记为完整事实正文。
- [ ] Step 4: 测试英文长标题不再被截成半句。
- [ ] Step 5: 测试低价值列表项不会直接通过可展示质量门槛。

### Task 3: 引入事件展示质量门槛

**Files:**

- Create: `info_aggregation/services/analysis/event_display_quality.py`
- Modify: `info_aggregation/services/analysis/event_builder.py`
- Modify: `info_aggregation/database/models.py`
- Modify: `info_aggregation/sql/mysql_schema_pro.sql`
- Create: `info_aggregation/sql/migration_v1.5.0_event_display_quality.sql`
- Test: `info_aggregation/tests/test_event_display_quality.py`
- Test: `info_aggregation/tests/test_event_rebuild_flow.py`

- [ ] Step 1: 设计并迁移事件展示质量字段，至少包含质量分和拦截原因。
- [ ] Step 2: 实现事件展示质量计算：来源数、完整来源数、低价值风险、分析质量。
- [ ] Step 3: 事件重建时根据质量结果设置 `active/monitoring/low_quality`。
- [ ] Step 4: 测试单来源弱小红书/微博事件进入 `monitoring`。
- [ ] Step 5: 测试多来源且至少一个完整来源的事件进入 `active`。

### Task 4: 升级规则分析和 validator

**Files:**

- Modify: `info_aggregation/services/event_analysis/rule_provider.py`
- Modify: `info_aggregation/services/event_analysis/validator.py`
- Modify: `info_aggregation/services/event_analysis/text_utils.py`
- Test: `info_aggregation/tests/test_event_analysis_pipeline.py`
- Test: `info_aggregation/tests/test_event_analysis_quality_report.py`

- [ ] Step 1: validator 增加低价值摘要、标题复读、半截英文、省略号裁剪检测。
- [ ] Step 2: 规则分析不再从低价值正文中直接取第一句做 `one_line_summary`。
- [ ] Step 3: 对弱来源输出线索态文案，例如“该主题正在形成热度线索，但当前缺少完整事实来源。”。
- [ ] Step 4: `what_happened` 和 `why_it_matters` 根据证据强弱调整语气。
- [ ] Step 5: 测试坏样本不会生成低价值一句话摘要。

### Task 5: 重构 LLM 事件分析输入、输出和审计

**Files:**

- Modify: `info_aggregation/services/event_analysis/providers.py`
- Modify: `info_aggregation/services/event_analysis/pipeline.py`
- Modify: `info_aggregation/services/event_analysis/schemas.py`
- Modify: `info_aggregation/services/analysis/llm_model_config.py`
- Modify: `info_aggregation/services/llm/chat.py`
- Test: `info_aggregation/tests/test_event_analysis_pipeline.py`
- Test: `info_aggregation/tests/test_llm_call_logging.py`
- Test: `info_aggregation/tests/test_event_analysis_model_selection.py`

- [ ] Step 1: LLM prompt 输入加入来源质量、风险原因、来源序号和 URL。
- [ ] Step 2: LLM 输出增加内部证据字段，同时兼容旧 `event_summary_snapshot`。
- [ ] Step 3: 事件分析 LLM 调用记录完整 request/response。
- [ ] Step 4: 当前模型失败时尝试下一个可用模型。
- [ ] Step 5: 测试 JSON 解析失败、超时、熔断时回退规则且记录原因。

### Task 6: info-serve 展示过滤和 API 输出增强

**Files:**

- Modify: `info-serve/internal/repository/event_store.go`
- Modify: `info-serve/internal/events/*.go`
- Test: `info-serve/internal/repository/*event*_test.go`

- [ ] Step 1: 用户端列表只返回 `active` 且展示质量达标事件。
- [ ] Step 2: 详情接口返回展示质量、证据链、弱来源原因和分析模式。
- [ ] Step 3: 管理端接口保留 `monitoring/low_quality` 查询能力。
- [ ] Step 4: 测试列表不会返回低质量事件。

### Task 7: info-admin 质量治理入口

**Files:**

- Modify: `info-admin/src/views/EventAnalysisQualityView.vue`
- Modify: `info-admin/src/views/EventAnalysisDetailView.vue`
- Modify: `info-admin/src/views/LLMModelsView.vue`
- Modify: `info-admin/src/services/api.ts`
- Test: `info-admin/src/**/*.test.ts`

- [ ] Step 1: 事件质量页增加展示状态、拦截原因、可用来源数。
- [ ] Step 2: 详情页展示某次分析使用的来源质量和 LLM 调用情况。
- [ ] Step 3: LLM 模型页展示熔断、成功率、平均耗时、最近失败原因。
- [ ] Step 4: 增加“补偿详情”和“重新分析”操作反馈。

### Task 8: info-mvp 可信情报流改造

**Files:**

- Modify: `info-mvp/src/components/EventList.vue`
- Modify: `info-mvp/src/pages/event-detail/event-detail.vue`
- Modify: `info-mvp/src/types/index.ts`
- Modify: `info-mvp/src/services/api.ts`
- Test: `info-mvp` H5 和小程序构建验证

- [ ] Step 1: 首页卡片增加可信度、阶段、来源数和最新变化表达。
- [ ] Step 2: 详情页强化证据链、风险提示、多源视角和发展脉络。
- [ ] Step 3: 对低可信字段使用谨慎文案，避免确定性误导。
- [ ] Step 4: H5 和小程序均验证文本不溢出、不重叠。

## 5. 实施顺序建议

推荐顺序：

1. Phase 0 + Task 1：先建立质量基线。
2. Phase 1 + Task 2：先堵住低质量数据继续扩大。
3. Phase 2 + Task 3 + Task 6：建立用户端展示门槛。
4. Phase 3 + Task 4：提升无 LLM 时的基础分析质量。
5. Phase 4 + Task 5：让 LLM 成为可靠增强器。
6. Phase 6 + Task 7：管理端治理闭环。
7. Phase 5 + Task 8：用户端体验升级。

不建议先做大规模 UI 改版。当前最影响用户感知的是数据和分析质量，必须先让首页只出现值得看的事件。

## 6. 验收指标

### 数据采集指标

- 文章型渠道完整详情率保持在 85% 以上。
- 热点/社交渠道低价值内容不直接进入 `active`。
- pending/detail_job backlog 有趋势下降，不长期堆积。

### 事件分析指标

- active 事件短摘要比例低于 5%。
- active 单来源弱事件比例低于 10%。
- `one_line_summary` 不出现 `hot。`、`new。`、`互动：点赞xx。`、纯分类字段。
- LLM 失败时 fallback 有记录，且不会产出坏摘要。

### 产品体验指标

- 用户端首页首屏展示 3-5 个可信事件，而不是散碎内容。
- 详情页能明确看到证据链和风险提示。
- 管理端能解释每个事件为什么展示或不展示。

## 7. 决策点

实施前需要确认以下产品策略：

1. 用户端是否只展示 `active` 事件，`monitoring` 仅管理端可见。
2. 微博/小红书是否默认作为热度信号，只有补偿成功或交叉验证后才变成可信事件。
3. LLM 是否允许多模型 fallback，例如 qwen 失败后自动尝试 DeepSeek。
4. 首页是否接受“数量减少但质量明显提升”的短期变化。

## 8. 本轮不做

- 不新增复杂推荐算法。
- 不做社交评论和社区互动。
- 不接付费订阅。
- 不重写四个服务架构。
- 不用 LLM 直接替代采集和事实校验。

这些可以作为下一阶段增长能力，但当前最重要的是先把“可信事件情报”打磨出来。
