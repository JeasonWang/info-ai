# 信息达人 Stage 06 高完整度采集框架 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为 `info_aggregation` 建立可复用的高完整度详情采集框架，并优先把微博渠道升级到多策略、高可信正文采集。

**Architecture:** 在现有 `BaseCrawler -> scheduler -> save -> fetch_detail` 链路上新增通用详情解析层，把详情采集拆成策略执行、内容归一化、有效性校验、完整度评分和采集证据记录五个环节。数据模型先在 `Info` 上补质量字段，再新增采集日志表承接每次详情策略执行记录，微博成为首个接入新框架的渠道。

**Tech Stack:** Python、FastAPI、SQLAlchemy、SQLite/MySQL、pytest、requests

---

## 文件与职责映射

- 修改：`info_aggregation/database/models.py`
  - 扩展 `Info` 详情质量字段，新增 `InfoAcquisitionLog` 模型。
- 修改：`info_aggregation/database/__init__.py`
  - 导出新增模型。
- 修改：`info_aggregation/sql/init_data.py`
  - 让模拟数据兼容新的详情质量状态。
- 创建：`info_aggregation/services/detail_pipeline.py`
  - 提供通用详情策略执行器、归一化、校验、评分与结果对象。
- 修改：`info_aggregation/crawlers/base.py`
  - 接入新详情流水线与统一状态返回。
- 修改：`info_aggregation/crawlers/weibo.py`
  - 将微博详情抓取改造成多策略解析器。
- 修改：`info_aggregation/scheduler/__init__.py`
  - 使用详情流水线更新 `Info` 质量字段并写采集日志。
- 创建：`info_aggregation/tests/test_detail_pipeline.py`
  - 覆盖通用详情流水线的校验与评分。
- 修改：`info_aggregation/tests/test_event_models.py`
  - 覆盖新增详情质量字段与采集日志表。
- 创建：`info_aggregation/tests/test_weibo_crawler_detail.py`
  - 覆盖微博多策略详情解析。
- 修改：`info_aggregation/tests/test_event_rebuild_flow.py`
  - 确认详情采集增强不破坏调度与事件重建。

### Task 1: 为详情质量状态补数据模型

**Files:**
- Modify: `info_aggregation/database/models.py`
- Modify: `info_aggregation/database/__init__.py`
- Modify: `info_aggregation/sql/init_data.py`
- Modify: `info_aggregation/tests/test_event_models.py`

- [ ] **Step 1: 先写失败的模型测试**

```python
def test_info_quality_fields_and_acquisition_logs_can_persist(session):
    category = Category(name="热点事件", code="hot", description="热点")
    session.add(category)
    session.flush()

    channel = Channel(
        name="微博",
        code="weibo",
        base_url="https://weibo.com",
        category_id=category.id,
        crawl_interval=30,
        is_active=1,
    )
    session.add(channel)
    session.flush()

    info = Info(
        title="微博热搜样例",
        content="列表摘要",
        category_id=category.id,
        channel_id=channel.id,
        source_id="wb-1",
        source_url="https://example.com/wb-1",
        detail_fetch_status="partial",
        detail_fetch_error="content_too_short",
        detail_strategy="topic_search",
        detail_score=72,
        detail_content_length=168,
    )
    session.add(info)
    session.flush()

    session.add(
        InfoAcquisitionLog(
            info_id=info.id,
            channel_code="weibo",
            strategy="topic_search",
            status="partial",
            score=72,
            content_length=168,
            failure_reason="content_too_short",
            matched_rules="short_content",
            raw_excerpt="微博正文样例",
        )
    )
    session.commit()

    saved = session.query(Info).first()
    assert saved.detail_fetch_status == "partial"
    assert saved.detail_strategy == "topic_search"
    assert saved.detail_score == 72
    assert session.query(InfoAcquisitionLog).count() == 1
```

- [ ] **Step 2: 运行测试确认先失败**

Run: `/Users/jeasonwang/IdeaProjects/info-ai/info_aggregation/.venv/bin/python -m pytest tests/test_event_models.py -q`
Expected: FAIL because `Info` does not yet expose the new fields or `InfoAcquisitionLog`.

- [ ] **Step 3: 实现最小模型改动**

```python
detail_fetch_status = Column(String(20), default="pending", comment="详情质量状态")
detail_fetch_error = Column(String(500), default="", comment="详情失败原因")
detail_strategy = Column(String(50), default="", comment="详情策略")
detail_score = Column(Integer, default=0, comment="详情完整度得分")
detail_content_length = Column(Integer, default=0, comment="详情正文长度")
detail_fetched_at = Column(DateTime, comment="详情抓取完成时间")
```

```python
class InfoAcquisitionLog(Base):
    __tablename__ = "info_acquisition_log"

    id = Column(Integer, primary_key=True, autoincrement=True)
    info_id = Column(Integer, ForeignKey("info.id"), nullable=False)
    channel_code = Column(String(50), default="", nullable=False)
    strategy = Column(String(50), default="", nullable=False)
    status = Column(String(20), default="", nullable=False)
    score = Column(Integer, default=0)
    content_length = Column(Integer, default=0)
    failure_reason = Column(String(255), default="")
    matched_rules = Column(String(500), default="")
    raw_excerpt = Column(Text, default="")
    created_at = Column(DateTime, default=datetime.now)
```

- [ ] **Step 4: 更新模拟数据默认状态**

```python
detail_fetch_status="complete",
detail_strategy="seed",
detail_score=100,
detail_content_length=len(item["content"]),
detail_fetched_at=now,
```

- [ ] **Step 5: 重新运行模型测试确认通过**

Run: `/Users/jeasonwang/IdeaProjects/info-ai/info_aggregation/.venv/bin/python -m pytest tests/test_event_models.py -q`
Expected: PASS

### Task 2: 建立通用详情流水线

**Files:**
- Create: `info_aggregation/services/detail_pipeline.py`
- Modify: `info_aggregation/crawlers/base.py`
- Create: `info_aggregation/tests/test_detail_pipeline.py`

- [ ] **Step 1: 写详情流水线失败测试**

```python
def test_pipeline_marks_shell_page_as_failed():
    result = run_detail_pipeline(
        title="微博热点",
        list_content="微博热点",
        strategy_results=[
            DetailStrategyResult(
                strategy="web_fallback",
                content="你访问的页面不见了 沪ICP备 营业执照",
            )
        ],
    )

    assert result.status == "failed"
    assert result.failure_reason == "shell_page"
    assert result.score == 0
```

```python
def test_pipeline_marks_multi_source_content_as_complete():
    result = run_detail_pipeline(
        title="OpenAI 新发布会",
        list_content="列表摘要",
        strategy_results=[
            DetailStrategyResult(
                strategy="topic_search",
                content="OpenAI 发布会上介绍了新模型、价格、开放计划。多位用户转发现场重点，并讨论开发者接入方式。",
            )
        ],
    )

    assert result.status == "complete"
    assert result.strategy == "topic_search"
    assert result.score >= 80
    assert result.content_length >= 40
```

- [ ] **Step 2: 运行测试确认先失败**

Run: `/Users/jeasonwang/IdeaProjects/info-ai/info_aggregation/.venv/bin/python -m pytest tests/test_detail_pipeline.py -q`
Expected: FAIL because `detail_pipeline.py` does not exist yet.

- [ ] **Step 3: 实现详情结果对象和流水线**

```python
@dataclass
class DetailStrategyResult:
    strategy: str
    content: str
    failure_reason: str = ""
    matched_rules: list[str] = field(default_factory=list)


@dataclass
class DetailPipelineResult:
    content: str
    status: str
    strategy: str
    score: int
    content_length: int
    failure_reason: str
    matched_rules: list[str]
```

```python
def run_detail_pipeline(title: str, list_content: str, strategy_results: list[DetailStrategyResult]) -> DetailPipelineResult:
    for candidate in strategy_results:
        normalized = normalize_content(candidate.content)
        status, reason, matched_rules = validate_content(title, normalized)
        score = score_content(title, normalized, matched_rules)
        if status in {"partial", "complete"}:
            return DetailPipelineResult(normalized, status, candidate.strategy, score, len(normalized), reason, matched_rules)
    fallback = normalize_content(list_content)
    return DetailPipelineResult(fallback, "list_only", "list_fallback", 10 if fallback else 0, len(fallback), "detail_unavailable", [])
```

- [ ] **Step 4: 在基类中接入统一 safe detail 能力**

```python
pipeline = self.resolve_detail(item)
if pipeline.status in {"partial", "complete"}:
    return pipeline.content, pipeline.status, pipeline.failure_reason, pipeline
return pipeline.content, pipeline.status, pipeline.failure_reason, pipeline
```

- [ ] **Step 5: 重新运行详情流水线测试**

Run: `/Users/jeasonwang/IdeaProjects/info-ai/info_aggregation/.venv/bin/python -m pytest tests/test_detail_pipeline.py -q`
Expected: PASS

### Task 3: 将微博升级为多策略详情解析器

**Files:**
- Modify: `info_aggregation/crawlers/weibo.py`
- Create: `info_aggregation/tests/test_weibo_crawler_detail.py`

- [ ] **Step 1: 先写微博多策略失败测试**

```python
def test_weibo_resolve_detail_prefers_topic_search_content():
    crawler = WeiboCrawler()
    crawler.fetch_json = fake_fetch_json

    result = crawler.resolve_detail({
        "title": "OpenAI 发布新模型",
        "content": "列表摘要",
        "source_url": "https://s.weibo.com/weibo?q=%23OpenAI 发布新模型%23",
    })

    assert result.status == "complete"
    assert result.strategy == "topic_search"
    assert "新模型" in result.content
```

```python
def test_weibo_resolve_detail_falls_back_to_list_only_when_all_strategies_fail():
    crawler = WeiboCrawler()
    crawler.fetch_json = lambda *args, **kwargs: {}

    result = crawler.resolve_detail({
        "title": "异常热搜",
        "content": "仅有列表摘要",
        "source_url": "https://example.com",
    })

    assert result.status == "list_only"
    assert result.strategy == "list_fallback"
```

- [ ] **Step 2: 运行微博详情测试确认先失败**

Run: `/Users/jeasonwang/IdeaProjects/info-ai/info_aggregation/.venv/bin/python -m pytest tests/test_weibo_crawler_detail.py -q`
Expected: FAIL because `WeiboCrawler` does not yet expose `resolve_detail`.

- [ ] **Step 3: 实现微博多策略详情解析**

```python
def resolve_detail(self, item: dict) -> DetailPipelineResult:
    candidates = [
        self._fetch_topic_search(item),
        self._fetch_hot_band_context(item),
        self._fetch_mobile_search(item),
        self._fetch_web_fallback(item),
    ]
    return run_detail_pipeline(
        title=item.get("title", ""),
        list_content=item.get("content", ""),
        strategy_results=[candidate for candidate in candidates if candidate],
    )
```

```python
def _fetch_topic_search(self, item: dict) -> DetailStrategyResult:
    word = item.get("title", "")
    data = self.fetch_json(f"https://weibo.com/ajax/search/topic?query={word}&page=1", headers=headers)
    statuses = data.get("data", {}).get("statuses", [])
    parts = [clean_status_text(status.get("text", "")) for status in statuses[:5]]
    return DetailStrategyResult(strategy="topic_search", content=" ".join(part for part in parts if part))
```

- [ ] **Step 4: 重新运行微博详情测试**

Run: `/Users/jeasonwang/IdeaProjects/info-ai/info_aggregation/.venv/bin/python -m pytest tests/test_weibo_crawler_detail.py -q`
Expected: PASS

### Task 4: 让调度链路写入质量状态和采集日志

**Files:**
- Modify: `info_aggregation/scheduler/__init__.py`
- Modify: `info_aggregation/tests/test_event_rebuild_flow.py`

- [ ] **Step 1: 写失败的调度联动测试**

```python
assert saved_info.detail_fetch_status == "complete"
assert saved_info.detail_strategy == "topic_search"
assert saved_info.detail_score >= 80
assert session.query(InfoAcquisitionLog).count() == 1
```

- [ ] **Step 2: 运行联动测试确认先失败**

Run: `/Users/jeasonwang/IdeaProjects/info-ai/info_aggregation/.venv/bin/python -m pytest tests/test_event_rebuild_flow.py -q`
Expected: FAIL because scheduler still only writes `success/failed`.

- [ ] **Step 3: 更新调度详情入库逻辑**

```python
detail_content, status, error_msg, pipeline = crawler.safe_fetch_detail(info.source_url, info.to_dict())
info.content = detail_content or original_content
info.detail_fetch_status = status
info.detail_fetch_error = error_msg
info.detail_strategy = pipeline.strategy
info.detail_score = pipeline.score
info.detail_content_length = pipeline.content_length
info.detail_fetched_at = datetime.now()
session.add(
    InfoAcquisitionLog(
        info_id=info.id,
        channel_code=channel_code,
        strategy=pipeline.strategy,
        status=status,
        score=pipeline.score,
        content_length=pipeline.content_length,
        failure_reason=error_msg,
        matched_rules=",".join(pipeline.matched_rules),
        raw_excerpt=(detail_content or original_content)[:200],
    )
)
```

- [ ] **Step 4: 重新运行联动测试**

Run: `/Users/jeasonwang/IdeaProjects/info-ai/info_aggregation/.venv/bin/python -m pytest tests/test_event_rebuild_flow.py -q`
Expected: PASS

### Task 5: 做阶段回归验证

**Files:**
- Verify: `info_aggregation/tests/test_event_models.py`
- Verify: `info_aggregation/tests/test_detail_pipeline.py`
- Verify: `info_aggregation/tests/test_weibo_crawler_detail.py`
- Verify: `info_aggregation/tests/test_event_rebuild_flow.py`
- Verify: `info_aggregation/tests/test_event_api.py`

- [ ] **Step 1: 跑新增后端测试集**

Run: `/Users/jeasonwang/IdeaProjects/info-ai/info_aggregation/.venv/bin/python -m pytest tests/test_event_models.py tests/test_detail_pipeline.py tests/test_weibo_crawler_detail.py tests/test_event_rebuild_flow.py -q`
Expected: PASS

- [ ] **Step 2: 跑事件 API 回归**

Run: `/Users/jeasonwang/IdeaProjects/info-ai/info_aggregation/.venv/bin/python -m pytest tests/test_event_api.py -q`
Expected: PASS

- [ ] **Step 3: 记录阶段完成状态**

```bash
git status --short
```

Expected: only the intended backend acquisition files and plan/spec changes are modified.
