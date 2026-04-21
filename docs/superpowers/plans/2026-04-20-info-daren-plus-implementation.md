# 信息达人 Plus Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 同时提升科技领域数据采集质量与用户侧信息消费体验，交付信息达人 `Plus` 版本。

**Architecture:** 后端继续沿用并扩展现有 `detail_pipeline`，把科技重点渠道升级为统一高完整度详情解析器，并补充轻量科技语义结构化与后台质量诊断。前端以首页、事件卡片、详情页为主进行信息层级重构，压缩无效占位，提升重点内容显著性，并保持列表到详情的连续阅读体验。

**Tech Stack:** Vue 3、TypeScript、Vue Router、Vitest、Python、FastAPI、SQLAlchemy、pytest、requests

---

## 文件与职责映射

- 修改：`info_aggregation/crawlers/csdn.py`
  - 将 CSDN 升级为统一详情解析器，优先获取科技类长文正文。
- 修改：`info_aggregation/crawlers/juejin.py`
  - 将掘金升级为统一详情解析器，增强开发工具与编程内容抓取质量。
- 修改：`info_aggregation/crawlers/kr36.py`
  - 为 36 氪科技内容补充多策略详情抓取。
- 创建：`info_aggregation/services/tech_content_parser.py`
  - 提供科技主题识别、实体抽取、关键词提取等轻量结构化能力。
- 修改：`info_aggregation/database/models.py`
  - 为 `Info` 增加科技语义字段，或新增结构化信息承载字段。
- 修改：`info_aggregation/api/__init__.py`
  - 扩展 `/api/infos` 和后台诊断接口返回科技质量信息。
- 修改：`info_aggregation/scheduler/__init__.py`
  - 在详情落库时同步写入科技结构化结果。
- 创建：`info_aggregation/tests/test_csdn_crawler_detail.py`
  - 覆盖 CSDN 详情解析策略。
- 创建：`info_aggregation/tests/test_juejin_crawler_detail.py`
  - 覆盖掘金详情解析策略。
- 创建：`info_aggregation/tests/test_kr36_crawler_detail.py`
  - 覆盖 36 氪详情解析策略。
- 创建：`info_aggregation/tests/test_tech_content_parser.py`
  - 覆盖科技内容轻量结构化。
- 修改：`info_aggregation/tests/test_event_api.py`
  - 覆盖新增科技质量返回字段。
- 修改：`info-max/src/views/HomeView.vue`
  - 重构首页首屏布局，压缩顶部占位。
- 修改：`info-max/src/components/EventList.vue`
  - 重排卡片信息层级，前置渠道和时间，缩小按钮。
- 修改：`info-max/src/views/EventDetailView.vue`
  - 继续优化事件详情页三层结构与重点内容显示。
- 修改：`info-max/src/views/InfoDetailView.vue`
  - 优化原始详情页可读性与信息层级。
- 修改：`info-max/src/views/SettingsView.vue`
  - 增强后台科技采集质量诊断。
- 修改：`info-max/src/styles.css`
  - 支撑 Plus 首页、卡片、详情页与后台面板样式。
- 修改：`info-max/src/types.ts`
  - 扩展事件卡片、原始信息、后台诊断所需前端类型。
- 修改：`info-max/src/services/api.ts`
  - 对齐新增接口字段。
- 修改：`info-max/src/views/__tests__/HomeView.spec.ts`
  - 覆盖首页首屏布局与轻量状态条。
- 修改：`info-max/src/components/__tests__/EventList.spec.ts`
  - 覆盖卡片信息重排与按钮缩小后的结构。
- 修改：`info-max/src/views/__tests__/EventDetailView.spec.ts`
  - 覆盖详情页三层展示逻辑。
- 创建：`info-max/src/views/__tests__/InfoDetailView.spec.ts`
  - 覆盖原始详情页的重点信息区域。
- 修改：`info-max/src/views/__tests__/SettingsView.spec.ts`
  - 覆盖后台科技质量诊断增强。
- 修改：`docs/开发文档/2026-04-20-Mac-M1-开发基线.md`
  - 补 Plus 阶段新增验证命令与开发顺序。

## 版本拆分

为了保证双主线能稳定交付，本计划拆成两个可连续执行的子阶段：

- `Plus-A`：科技数据底座增强第一轮 + 首页/卡片/详情页主体验重构
- `Plus-B`：科技语义结构化增强 + 后台趋势诊断增强 + 第二批体验打磨

本次 implementation plan 聚焦 `Plus-A`，保证每个任务都能直接落到当前代码库。

---

### Task 1: 为科技内容建立轻量结构化能力

**Files:**
- Create: `info_aggregation/services/tech_content_parser.py`
- Modify: `info_aggregation/tests/test_tech_content_parser.py`
- Modify: `info_aggregation/services/__init__.py`

- [ ] **Step 1: 先写失败的结构化测试**

```python
from services.tech_content_parser import parse_tech_content


def test_parse_tech_content_extracts_topic_entity_and_keywords():
    result = parse_tech_content(
        title="英伟达发布H200芯片",
        content="H200 芯片面向大模型训练场景，开发者开始讨论显存、训练效率和部署成本。",
    )

    assert result.topic_type == "chip_release"
    assert "英伟达" in result.entities
    assert "H200" in result.entities
    assert "显存" in result.keywords
    assert "训练效率" in result.keywords
```

- [ ] **Step 2: 运行测试确认先失败**

Run: `/Users/jeasonwang/IdeaProjects/info-ai/info_aggregation/.venv/bin/python -m pytest tests/test_tech_content_parser.py -q`
Expected: FAIL because `tech_content_parser.py` does not exist yet.

- [ ] **Step 3: 写最小结构化实现**

```python
from dataclasses import dataclass, field
import re


@dataclass
class TechContentParseResult:
    topic_type: str
    entities: list[str] = field(default_factory=list)
    keywords: list[str] = field(default_factory=list)


TOPIC_RULES = {
    "chip_release": ["芯片", "GPU", "显卡", "H100", "H200", "CUDA"],
    "model_release": ["模型", "大模型", "推理", "上下文", "token"],
    "dev_tool": ["编程", "开发者", "IDE", "API", "Agent", "框架"],
}


def parse_tech_content(title: str, content: str) -> TechContentParseResult:
    text = f"{title} {content}"
    topic_type = "general_tech"
    for candidate, markers in TOPIC_RULES.items():
        if any(marker in text for marker in markers):
            topic_type = candidate
            break

    entities = []
    for marker in ["OpenAI", "Anthropic", "英伟达", "H100", "H200", "CUDA", "MCP", "Agent"]:
        if marker in text and marker not in entities:
            entities.append(marker)

    keywords = []
    for keyword in ["显存", "训练效率", "部署成本", "推理", "训练", "token", "API", "上下文长度"]:
        if keyword in text and keyword not in keywords:
            keywords.append(keyword)

    return TechContentParseResult(topic_type=topic_type, entities=entities, keywords=keywords)
```

- [ ] **Step 4: 运行测试确认通过**

Run: `/Users/jeasonwang/IdeaProjects/info-ai/info_aggregation/.venv/bin/python -m pytest tests/test_tech_content_parser.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add info_aggregation/services/tech_content_parser.py info_aggregation/tests/test_tech_content_parser.py info_aggregation/services/__init__.py
git commit -m "feat: add tech content parser"
```

### Task 2: 扩展 Info 以保存科技结构化信息

**Files:**
- Modify: `info_aggregation/database/models.py`
- Modify: `info_aggregation/database/__init__.py`
- Modify: `info_aggregation/tests/test_event_models.py`

- [ ] **Step 1: 先写失败的模型测试**

```python
def test_info_can_persist_tech_semantic_fields(session):
    info = Info(
        title="英伟达发布H200芯片",
        content="H200 芯片面向大模型训练场景。",
        category_id=1,
        channel_id=1,
        source_id="chip-1",
        source_url="https://example.com/chip-1",
        tech_topic_type="chip_release",
        tech_entities="英伟达,H200",
        tech_keywords="显存,训练效率",
    )
    session.add(info)
    session.commit()

    saved = session.query(Info).filter(Info.source_id == "chip-1").first()
    assert saved.tech_topic_type == "chip_release"
    assert saved.tech_entities == "英伟达,H200"
    assert saved.tech_keywords == "显存,训练效率"
```

- [ ] **Step 2: 运行测试确认先失败**

Run: `/Users/jeasonwang/IdeaProjects/info-ai/info_aggregation/.venv/bin/python -m pytest tests/test_event_models.py -q`
Expected: FAIL because new semantic fields do not exist yet.

- [ ] **Step 3: 最小化扩展模型**

```python
tech_topic_type = Column(String(50), default="", comment="科技主题类型")
tech_entities = Column(String(500), default="", comment="科技核心实体，逗号分隔")
tech_keywords = Column(String(500), default="", comment="科技关键词，逗号分隔")
```

- [ ] **Step 4: 运行模型测试确认通过**

Run: `/Users/jeasonwang/IdeaProjects/info-ai/info_aggregation/.venv/bin/python -m pytest tests/test_event_models.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add info_aggregation/database/models.py info_aggregation/database/__init__.py info_aggregation/tests/test_event_models.py
git commit -m "feat: persist tech semantic fields"
```

### Task 3: 将 CSDN 接入统一高完整度详情流水线

**Files:**
- Modify: `info_aggregation/crawlers/csdn.py`
- Create: `info_aggregation/tests/test_csdn_crawler_detail.py`

- [ ] **Step 1: 先写失败的渠道测试**

```python
from crawlers.csdn import CsdnCrawler


def test_csdn_resolve_detail_prefers_article_content():
    crawler = CsdnCrawler()

    class DummyResponse:
        text = """
        <html><body>
          <article>
            <h1>MCP 工具链实践</h1>
            <p>文章详细介绍了 MCP 在开发工具集成中的实际用法，以及 Agent 协作调度方式。</p>
          </article>
        </body></html>
        """

    crawler.fetch = lambda *args, **kwargs: DummyResponse()

    result = crawler.resolve_detail(
        {"title": "MCP 工具链实践", "content": "列表摘要", "source_url": "https://example.com/post"}
    )

    assert result.status == "complete"
    assert result.strategy == "fetch_detail"
    assert "Agent 协作调度方式" in result.content
```

- [ ] **Step 2: 运行测试确认先失败**

Run: `/Users/jeasonwang/IdeaProjects/info-ai/info_aggregation/.venv/bin/python -m pytest tests/test_csdn_crawler_detail.py -q`
Expected: FAIL because test file does not exist or crawler does not expose `resolve_detail`.

- [ ] **Step 3: 用基类统一详情流水线补齐 CSDN**

```python
def fetch_detail(self, source_url: str, item: dict) -> str:
    headers = self._build_headers()
    response = self.fetch(source_url, headers=headers, timeout=15)
    return self._extract_text_from_html(response.text)
```

- [ ] **Step 4: 运行测试确认通过**

Run: `/Users/jeasonwang/IdeaProjects/info-ai/info_aggregation/.venv/bin/python -m pytest tests/test_csdn_crawler_detail.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add info_aggregation/crawlers/csdn.py info_aggregation/tests/test_csdn_crawler_detail.py
git commit -m "feat: add high-fidelity detail flow for csdn"
```

### Task 4: 将掘金接入统一高完整度详情流水线

**Files:**
- Modify: `info_aggregation/crawlers/juejin.py`
- Create: `info_aggregation/tests/test_juejin_crawler_detail.py`

- [ ] **Step 1: 先写失败测试**

```python
from crawlers.juejin import JuejinCrawler


def test_juejin_resolve_detail_extracts_long_article():
    crawler = JuejinCrawler()

    class DummyResponse:
        text = """
        <html><body>
          <article>
            <h1>Agent 工程实践</h1>
            <p>文章讨论了 Agent 在多步骤任务执行中的编排方式、工具调用和上下文管理。</p>
          </article>
        </body></html>
        """

    crawler.fetch = lambda *args, **kwargs: DummyResponse()

    result = crawler.resolve_detail(
        {"title": "Agent 工程实践", "content": "列表摘要", "source_url": "https://example.com/juejin"}
    )

    assert result.status == "complete"
    assert "工具调用和上下文管理" in result.content
```

- [ ] **Step 2: 运行测试确认先失败**

Run: `/Users/jeasonwang/IdeaProjects/info-ai/info_aggregation/.venv/bin/python -m pytest tests/test_juejin_crawler_detail.py -q`
Expected: FAIL

- [ ] **Step 3: 复用基类详情流水线实现掘金详情**

```python
def fetch_detail(self, source_url: str, item: dict) -> str:
    response = self.fetch(source_url, headers=self._build_headers(), timeout=15)
    return self._extract_text_from_html(response.text)
```

- [ ] **Step 4: 运行测试确认通过**

Run: `/Users/jeasonwang/IdeaProjects/info-ai/info_aggregation/.venv/bin/python -m pytest tests/test_juejin_crawler_detail.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add info_aggregation/crawlers/juejin.py info_aggregation/tests/test_juejin_crawler_detail.py
git commit -m "feat: add high-fidelity detail flow for juejin"
```

### Task 5: 增强 36 氪科技详情解析

**Files:**
- Modify: `info_aggregation/crawlers/kr36.py`
- Create: `info_aggregation/tests/test_kr36_crawler_detail.py`

- [ ] **Step 1: 先写失败测试**

```python
from crawlers.kr36 import Kr36Crawler


def test_kr36_resolve_detail_keeps_article_context():
    crawler = Kr36Crawler()

    class DummyResponse:
        text = """
        <html><body>
          <article>
            <h1>OpenAI 推出新 Agent 工具</h1>
            <p>报道重点涉及 API 接入、开发者工具链，以及企业侧工作流自动化场景。</p>
          </article>
        </body></html>
        """

    crawler.fetch = lambda *args, **kwargs: DummyResponse()

    result = crawler.resolve_detail(
        {"title": "OpenAI 推出新 Agent 工具", "content": "列表摘要", "source_url": "https://example.com/36kr"}
    )

    assert result.status == "complete"
    assert "工作流自动化场景" in result.content
```

- [ ] **Step 2: 运行测试确认先失败**

Run: `/Users/jeasonwang/IdeaProjects/info-ai/info_aggregation/.venv/bin/python -m pytest tests/test_kr36_crawler_detail.py -q`
Expected: FAIL

- [ ] **Step 3: 最小实现 36 氪详情抽取**

```python
def fetch_detail(self, source_url: str, item: dict) -> str:
    response = self.fetch(source_url, headers=self._build_headers(), timeout=15)
    return self._extract_text_from_html(response.text)
```

- [ ] **Step 4: 运行测试确认通过**

Run: `/Users/jeasonwang/IdeaProjects/info-ai/info_aggregation/.venv/bin/python -m pytest tests/test_kr36_crawler_detail.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add info_aggregation/crawlers/kr36.py info_aggregation/tests/test_kr36_crawler_detail.py
git commit -m "feat: add high-fidelity detail flow for 36kr"
```

### Task 6: 在调度链路中写入科技结构化结果

**Files:**
- Modify: `info_aggregation/scheduler/__init__.py`
- Modify: `info_aggregation/tests/test_event_rebuild_flow.py`

- [ ] **Step 1: 先写失败测试**

```python
def test_fetch_details_persists_tech_semantic_fields(session, monkeypatch):
    # 构建一条科技类 Info，执行详情抓取后断言 tech_topic_type / tech_entities / tech_keywords 被写回
    ...
    assert refreshed.tech_topic_type == "chip_release"
    assert "英伟达" in refreshed.tech_entities
```

- [ ] **Step 2: 运行测试确认先失败**

Run: `/Users/jeasonwang/IdeaProjects/info-ai/info_aggregation/.venv/bin/python -m pytest tests/test_event_rebuild_flow.py -q`
Expected: FAIL because scheduler does not write semantic fields yet.

- [ ] **Step 3: 在详情更新时调用解析器**

```python
semantic = parse_tech_content(info.title, info.content)
info.tech_topic_type = semantic.topic_type
info.tech_entities = ",".join(semantic.entities)
info.tech_keywords = ",".join(semantic.keywords)
```

- [ ] **Step 4: 运行测试确认通过**

Run: `/Users/jeasonwang/IdeaProjects/info-ai/info_aggregation/.venv/bin/python -m pytest tests/test_event_rebuild_flow.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add info_aggregation/scheduler/__init__.py info_aggregation/tests/test_event_rebuild_flow.py
git commit -m "feat: persist tech semantic data in scheduler"
```

### Task 7: 扩展后台科技质量诊断接口数据

**Files:**
- Modify: `info_aggregation/api/__init__.py`
- Modify: `info_aggregation/tests/test_event_api.py`

- [ ] **Step 1: 先写失败测试**

```python
def test_list_infos_returns_tech_semantic_fields(session):
    ...
    target = next(item for item in payload["items"] if item["source_id"] == "tech-1")
    assert target["tech_topic_type"] == "chip_release"
    assert "英伟达" in target["tech_entities"]
    assert "显存" in target["tech_keywords"]
```

- [ ] **Step 2: 运行测试确认先失败**

Run: `/Users/jeasonwang/IdeaProjects/info-ai/info_aggregation/.venv/bin/python -m pytest tests/test_event_api.py -q`
Expected: FAIL because API does not expose new fields yet.

- [ ] **Step 3: 扩展接口返回字段**

```python
"tech_topic_type": info.tech_topic_type,
"tech_entities": info.tech_entities.split(",") if info.tech_entities else [],
"tech_keywords": info.tech_keywords.split(",") if info.tech_keywords else [],
```

- [ ] **Step 4: 运行测试确认通过**

Run: `/Users/jeasonwang/IdeaProjects/info-ai/info_aggregation/.venv/bin/python -m pytest tests/test_event_api.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add info_aggregation/api/__init__.py info_aggregation/tests/test_event_api.py
git commit -m "feat: expose tech semantic fields in api"
```

### Task 8: 重构首页首屏为轻量状态条

**Files:**
- Modify: `info-max/src/views/HomeView.vue`
- Modify: `info-max/src/views/__tests__/HomeView.spec.ts`
- Modify: `info-max/src/styles.css`

- [ ] **Step 1: 先写失败测试**

```ts
it('renders compact channel and event summary instead of large metric cards', async () => {
  ...
  expect(wrapper.text()).toContain('当前频道')
  expect(wrapper.text()).toContain('事件数量')
  expect(wrapper.findAll('.event-hero__metric')).toHaveLength(0)
  expect(wrapper.find('.event-hero__status-bar').exists()).toBe(true)
})
```

- [ ] **Step 2: 运行测试确认先失败**

Run: `npm test -- src/views/__tests__/HomeView.spec.ts`
Expected: FAIL because homepage still renders large metric cards.

- [ ] **Step 3: 最小实现首页首屏重构**

```vue
<div class="event-hero__status-bar">
  <span>当前频道：{{ activeCategoryName }}</span>
  <span>事件数量：{{ eventPage.total }}</span>
</div>
```

- [ ] **Step 4: 更新样式**

```css
.event-hero__status-bar {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  color: var(--text-subtle);
  font-size: 0.92rem;
}
```

- [ ] **Step 5: 运行测试确认通过**

Run: `npm test -- src/views/__tests__/HomeView.spec.ts`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add info-max/src/views/HomeView.vue info-max/src/views/__tests__/HomeView.spec.ts info-max/src/styles.css
git commit -m "feat: simplify home hero for plus"
```

### Task 9: 重排事件卡片信息层级

**Files:**
- Modify: `info-max/src/components/EventList.vue`
- Modify: `info-max/src/components/__tests__/EventList.spec.ts`
- Modify: `info-max/src/styles.css`

- [ ] **Step 1: 先写失败测试**

```ts
it('renders channel before title and keeps compact action buttons', () => {
  ...
  expect(wrapper.text()).toContain('微博')
  expect(wrapper.text()).toContain('2026-04-19 12:30:00')
  expect(wrapper.findAll('.event-card__action-button')).toHaveLength(2)
})
```

- [ ] **Step 2: 运行测试确认先失败**

Run: `npm test -- src/components/__tests__/EventList.spec.ts`
Expected: FAIL because channel still lives in source badges and action buttons are not compact.

- [ ] **Step 3: 最小实现卡片重排**

```vue
<div class="info-card__top">
  <span class="tag">{{ item.source_badges[0] || item.primary_category.name }}</span>
  <span class="panel__meta">{{ formatDateTime(item.last_updated_at) }}</span>
</div>
```

```vue
<div class="info-card__actions event-card__actions">
  <RouterLink class="button button--primary event-card__action-button" ...>查看时间线</RouterLink>
  <RouterLink class="button button--ghost event-card__action-button" ...>查看详情</RouterLink>
</div>
```

- [ ] **Step 4: 更新样式**

```css
.event-card__action-button {
  min-height: 38px;
  padding: 0 14px;
}
```

- [ ] **Step 5: 运行测试确认通过**

Run: `npm test -- src/components/__tests__/EventList.spec.ts`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add info-max/src/components/EventList.vue info-max/src/components/__tests__/EventList.spec.ts info-max/src/styles.css
git commit -m "feat: reorder event cards for plus"
```

### Task 10: 继续优化事件详情页三层结构

**Files:**
- Modify: `info-max/src/views/EventDetailView.vue`
- Modify: `info-max/src/views/__tests__/EventDetailView.spec.ts`
- Modify: `info-max/src/styles.css`

- [ ] **Step 1: 先写失败测试**

```ts
it('renders summary, progress and evidence in three distinct sections', async () => {
  ...
  expect(wrapper.text()).toContain('重点结论')
  expect(wrapper.text()).toContain('最新进展')
  expect(wrapper.text()).toContain('代表性原始来源')
  expect(wrapper.find('.detail-hero__focus').exists()).toBe(true)
})
```

- [ ] **Step 2: 运行测试确认先失败**

Run: `npm test -- src/views/__tests__/EventDetailView.spec.ts`
Expected: FAIL because page does not yet fully separate progress and evidence visually.

- [ ] **Step 3: 最小实现层级增强**

```vue
<section class="panel detail-evidence">
  <EventTimeline :items="detail.timeline" />
  <EventSummaryPanels ... />
</section>
```

- [ ] **Step 4: 更新样式**

```css
.detail-evidence {
  display: grid;
  gap: 18px;
}
```

- [ ] **Step 5: 运行测试确认通过**

Run: `npm test -- src/views/__tests__/EventDetailView.spec.ts`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add info-max/src/views/EventDetailView.vue info-max/src/views/__tests__/EventDetailView.spec.ts info-max/src/styles.css
git commit -m "feat: refine event detail hierarchy for plus"
```

### Task 11: 优化原始详情页可读性

**Files:**
- Modify: `info-max/src/views/InfoDetailView.vue`
- Modify: `info-max/src/views/__tests__/InfoDetailView.spec.ts`
- Modify: `info-max/src/styles.css`

- [ ] **Step 1: 先写失败测试**

```ts
it('renders key source metadata in a compact readable header', async () => {
  ...
  expect(wrapper.text()).toContain('事件时间')
  expect(wrapper.text()).toContain('核心主体')
  expect(wrapper.text()).toContain('打开原始来源')
})
```

- [ ] **Step 2: 运行测试确认先失败**

Run: `npm test -- src/views/__tests__/InfoDetailView.spec.ts`
Expected: FAIL because test file is missing or view is not verified yet.

- [ ] **Step 3: 最小实现详情头部压缩**

```vue
<section class="panel detail-hero detail-hero--compact">
  ...
</section>
```

- [ ] **Step 4: 更新样式**

```css
.detail-hero--compact .detail-grid {
  gap: 12px;
}
```

- [ ] **Step 5: 运行测试确认通过**

Run: `npm test -- src/views/__tests__/InfoDetailView.spec.ts`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add info-max/src/views/InfoDetailView.vue info-max/src/views/__tests__/InfoDetailView.spec.ts info-max/src/styles.css
git commit -m "feat: improve source detail readability for plus"
```

### Task 12: 增强后台科技采集质量诊断

**Files:**
- Modify: `info-max/src/views/SettingsView.vue`
- Modify: `info-max/src/views/__tests__/SettingsView.spec.ts`
- Modify: `info-max/src/types.ts`
- Modify: `info-max/src/styles.css`

- [ ] **Step 1: 先写失败测试**

```ts
it('shows tech topic type and keyword diagnostics in settings', async () => {
  ...
  expect(wrapper.text()).toContain('科技主题')
  expect(wrapper.text()).toContain('关键词')
})
```

- [ ] **Step 2: 运行测试确认先失败**

Run: `npm test -- src/views/__tests__/SettingsView.spec.ts`
Expected: FAIL because settings page does not surface tech semantic information yet.

- [ ] **Step 3: 最小实现后台科技诊断展示**

```vue
<div class="info-card__meta">
  <span>科技主题：{{ info.tech_topic_type || '未识别' }}</span>
  <span>关键词：{{ (info.tech_keywords || []).join('、') || '暂无' }}</span>
</div>
```

- [ ] **Step 4: 运行测试确认通过**

Run: `npm test -- src/views/__tests__/SettingsView.spec.ts`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add info-max/src/views/SettingsView.vue info-max/src/views/__tests__/SettingsView.spec.ts info-max/src/types.ts info-max/src/styles.css
git commit -m "feat: add tech diagnostics to settings"
```

### Task 13: 更新开发文档与整体验证

**Files:**
- Modify: `docs/开发文档/2026-04-20-Mac-M1-开发基线.md`

- [ ] **Step 1: 补充 Plus 阶段验证命令**

```md
前端：
- `npm test -- src/components/__tests__/EventList.spec.ts src/views/__tests__/HomeView.spec.ts src/views/__tests__/EventDetailView.spec.ts src/views/__tests__/InfoDetailView.spec.ts src/views/__tests__/SettingsView.spec.ts`
- `npm run build`

后端：
- `/Users/jeasonwang/IdeaProjects/info-ai/info_aggregation/.venv/bin/python -m pytest tests/test_detail_pipeline.py tests/test_weibo_crawler_detail.py tests/test_toutiao_crawler_detail.py tests/test_csdn_crawler_detail.py tests/test_juejin_crawler_detail.py tests/test_kr36_crawler_detail.py tests/test_tech_content_parser.py tests/test_event_rebuild_flow.py tests/test_event_api.py tests/test_event_models.py -q`
```

- [ ] **Step 2: 运行前端组合验证**

Run: `npm test -- src/components/__tests__/EventList.spec.ts src/views/__tests__/HomeView.spec.ts src/views/__tests__/EventDetailView.spec.ts src/views/__tests__/InfoDetailView.spec.ts src/views/__tests__/SettingsView.spec.ts`
Expected: PASS

- [ ] **Step 3: 运行前端构建**

Run: `npm run build`
Expected: PASS

- [ ] **Step 4: 运行后端组合验证**

Run: `/Users/jeasonwang/IdeaProjects/info-ai/info_aggregation/.venv/bin/python -m pytest tests/test_detail_pipeline.py tests/test_weibo_crawler_detail.py tests/test_toutiao_crawler_detail.py tests/test_csdn_crawler_detail.py tests/test_juejin_crawler_detail.py tests/test_kr36_crawler_detail.py tests/test_tech_content_parser.py tests/test_event_rebuild_flow.py tests/test_event_api.py tests/test_event_models.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add docs/开发文档/2026-04-20-Mac-M1-开发基线.md
git commit -m "docs: update mac m1 baseline for plus"
```

---

## Self-Review

- `Plus` 设计文档中的双主线目标已覆盖到任务：
  - 数据采集与质量：Task 1-7
  - 用户侧体验：Task 8-12
  - 文档与验证：Task 13
- 未保留 `TBD / TODO / implement later` 这类占位语句
- 所有新增类型、字段与文件路径在任务中均有落点
- 本计划聚焦 `Plus-A`，没有把 `Plus-B` 的趋势分析、第二批渠道扩展强行塞进本轮实现，范围可控
