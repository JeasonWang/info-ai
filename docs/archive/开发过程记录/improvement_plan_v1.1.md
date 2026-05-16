# 信息达人 v1.1 改进工作计划

> 计划版本：v1.1.0
> 生成时间：2026-05-11
> 当前版本基线：v1.0.0 (cb05afd)
> 2026-05-12 自测修复状态：核心代码与数据库结构已按本计划收敛，详见文末“执行验收记录”。

---

## 一、改进目标

本次迭代围绕三个核心能力进行升级：

1. **Cookie 数据库化** — 从 .env 文件迁移到数据库，支持管理端热更新
2. **事件溯源能力** — 记录分析来源，引入历史脉络和前因后果分析
3. **数据库瘦身** — 清理废弃表和冗余字段，降低维护成本

---

## 二、总体阶段划分

```
Phase 1: Cookie 数据库化（2天）
Phase 2: 事件溯源能力（4天）
Phase 3: 事件历史脉络分析（3天）
Phase 4: 数据库瘦身（1天）
Phase 5: 增量事件构建（3天）
```

总工期：**约13个工作日**

---

## 执行验收记录（2026-05-12）

本轮修复完成以下收敛项：

- Cookie 数据库化：`CredentialProvider` 支持环境变量 / `.env` / 数据库三层读取，环境变量和 `.env` 实时优先；管理端清除凭证会真实清空 `channel.cookies` 和 `extra_credentials`。
- 2026-05-12 补充：渠道 Cookie / ZSE 的正式入口调整为数据库优先，env 仅保留旧脚本兜底；初始化脚本会写入 `status=sample` 的格式样例，采集器不会把样例当成有效登录态。
- 事件溯源：全量和增量事件分析都会写入 `event_analysis_source`，管理端可查看分析运行和来源明细。
- 历史脉络：事件模型、演变记录、分析 prompt 历史上下文已接入；增量补偿后可基于现有事件来源重新分析。
- 数据库瘦身：`channel.crawl_interval`、`crawl_health_snapshot`、`user_follow_keyword` 已从当前 schema/代码路径移除，旧库通过迁移脚本清理。
- 增量构建：无 checkpoint 时会从已有关联最大 `info_id` 推断基线，避免全量重建后重复追加；新增 Info 会增量刷新事件分析和溯源。

已执行自测：

```bash
cd info_aggregation && ./.venv/bin/python -m pytest -q
cd info-serve && env GOCACHE=/tmp/info-serve-go-build-cache go test ./...
cd info-admin && npm test -- --run
cd info-admin && npm run build
```

本地 MySQL 验证：

```bash
DB_TYPE=mysql DB_HOST=127.0.0.1 DB_PORT=3306 DB_USER=root DB_PASSWORD=root1234 DB_NAME=info-max \
  ./.venv/bin/python -c "from database import get_session, EventAnalysisSource; from services import rebuild_events; s=get_session(); rebuild_events(s, limit=200, mode='full'); print(s.query(EventAnalysisSource).count()); s.close()"
```

---

## 三、Phase 1 — Cookie 数据库化

### 1.1 目标

将微博、小红书、知乎的 Cookie/凭证从 `.env` 文件迁移到 `channel` 表，支持管理端页面查看状态、更新配置、测试连接。

### 1.2 涉及的表变更

**表：channel**（ALTER）

```sql
ALTER TABLE channel
  ADD COLUMN cookies TEXT DEFAULT '' COMMENT '采集Cookie凭证(JSON格式)',
  ADD COLUMN extra_credentials JSON DEFAULT NULL COMMENT '扩展凭证(知乎zse_93/zse_96等)',
  ADD COLUMN credentials_updated_at DATETIME DEFAULT NULL COMMENT '凭证最后更新时间',
  ADD COLUMN credentials_updated_by VARCHAR(100) DEFAULT '' COMMENT '最后更新人';

ALTER TABLE channel
  DROP COLUMN crawl_interval;  -- 冗余字段，一并清理
```

> `cookies` 字段存储格式：
> ```json
> {
>   "cookie": "SUB=xxx; SUBP=xxx",
>   "user_agent": "Mozilla/5.0...",
>   "last_verified_at": "2026-05-10T10:00:00Z",
>   "status": "active"  // active / expired / invalid
> }
> ```

> `extra_credentials` 字段存储格式：
> ```json
> {
>   "zhihu": {"zse_93": "101_3_3.0", "zse_96": "2.0_..."},
>   "generic": {"Authorization": "Bearer xxx"}
> }
> ```

### 1.3 涉及的代码变更

#### 1.3.1 Python 层

**文件：`info_aggregation/database/models.py`**
- `Channel` 模型新增字段：`cookies`、`extra_credentials`、`credentials_updated_at`、`credentials_updated_by`
- `Channel.to_dict()` 新增字段输出

**文件：`info_aggregation/services/collection/credential_provider.py`**
- 重构 `get()` 和 `get_with_source()` 方法
- 优先级调整为：`环境变量 > .env > 数据库`
- 新增 `_read_db_credential()` 方法：从 channel 表读取凭证
- 新增 `invalidate_cache()` 方法：凭证更新后清除缓存
- 新增 `verify_credential()` 方法：验证凭证有效性（通过测试请求）

**文件：`info_aggregation/config.py`**
- 移除 `ZHIHU_COOKIE`、`WEIBO_COOKIE`、`XHS_COOKIE` 等环境变量（作为 fallback 保留，标记为 deprecated）

**文件：`info_aggregation/api/__init__.py`**（Python FastAPI）
- 新增 `PUT /api/admin/channels/{channel_code}/credentials` — 更新凭证
- 新增 `GET /api/admin/channels/{channel_code}/credentials` — 读取凭证状态（脱敏）
- 新增 `POST /api/admin/channels/{channel_code}/credentials/test` — 测试凭证有效性
- 新增 `DELETE /api/admin/channels/{channel_code}/credentials` — 清除凭证
- 修改 `GET /api/admin/channels` — 列表中包含凭证状态摘要字段

**文件：`info_aggregation/crawlers/weibo.py`、`zhihu.py`、`xiaohongshu.py`**
- 将 `_get_*_cookie()` 方法改为调用 `CredentialProvider.get()`

#### 1.3.2 Go 层

**文件：`info-serve/internal/repository/admin_store.go`**
- `GetChannelCredentials()` — 查询渠道凭证状态（脱敏）
- `UpdateChannelCredentials()` — 更新渠道凭证
- `TestChannelCredentials()` — 测试凭证（代理到 Python API）

**文件：`info-serve/internal/admin/service.go`**
- `Store` 接口新增：`GetChannelCredentials`、`UpdateChannelCredentials`、`TestChannelCredentials`
- `Service` 结构体新增对应方法

**文件：`info-serve/internal/transport/http/handler.go`**
- 新增路由：`PUT /api/admin/channels/:code/credentials`
- 新增路由：`GET /api/admin/channels/:code/credentials`
- 新增路由：`POST /api/admin/channels/:code/credentials/test`
- 新增路由：`DELETE /api/admin/channels/:code/credentials`

#### 1.3.3 前端（info-admin）

**新增页面/组件：**
- `src/views/channel/CredentialTab.vue` — 渠道凭证管理 Tab
- 嵌入在现有的渠道详情/编辑页面中

**功能点：**
- 显示当前 Cookie 配置状态（active / expired / not_configured）
- 脱敏展示：显示前4后4字符，如 `SUB=xxx...xxx`
- 文本框：粘贴完整 Cookie
- 额外凭证配置（zse_93 / zse_96 等）
- "测试连接" 按钮：触发 Python API 并显示结果
- 凭证更新后自动触发 `CredentialProvider.invalidate_cache()`

### 1.4 测试计划

| 测试项 | 验证点 |
|--------|--------|
| 凭证写入 | 从前端更新 Cookie → 读数据库确认存储正确 |
| 凭证读取 | Python 爬虫启动 → 确认从数据库读取到 Cookie |
| 优先级覆盖 | 设置环境变量 → 确认环境变量优先于数据库 |
| 过期回退 | 移除环境变量 → 确认回退到数据库 |
| 测试连接 | 输入正确 Cookie → 返回 success；输入错误 → 返回 failure + 原因 |
| 审计记录 | 更新凭证 → 查询审计日志确认记录 |

---

## 四、Phase 2 — 事件溯源能力

### 2.1 目标

记录每次事件分析的具体信息来源（具体用了哪些 Info），打通"分析结论 → 原始数据"的追溯链路。

### 2.2 涉及的表变更

**新增表：event_analysis_source（分析来源追溯表）**

```sql
CREATE TABLE event_analysis_source (
    id INT PRIMARY KEY AUTO_INCREMENT,
    run_id INT NOT NULL COMMENT '分析运行ID，对应 event_analysis_run.id',
    info_id INT NOT NULL COMMENT '信息源ID，对应 info.id',
    info_title VARCHAR(200) DEFAULT '' COMMENT '信息标题快照(去关联查表)',
    role VARCHAR(20) DEFAULT 'media' COMMENT '角色: primary/media/background',
    weight INT DEFAULT 0 COMMENT '权重(来自质量分)',
    quality_score INT DEFAULT 0 COMMENT '当时该条信息的质量分',
    is_analyzed TINYINT DEFAULT 1 COMMENT '是否被分析使用(淘汰项标记)',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,

    INDEX idx_run_id (run_id),
    INDEX idx_info_id (info_id),
    UNIQUE KEY uq_run_info (run_id, info_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='事件分析的信息来源追溯表';
```

### 2.3 涉及的代码变更

#### 2.3.1 Python 层

**文件：`info_aggregation/database/models.py`**
- 新增 `EventAnalysisSource` 模型

**文件：`info_aggregation/services/analysis/event_builder.py`**
- `rebuild_events()` 中，创建 `EventAnalysisRun` 后，新增写入 `EventAnalysisSource` 记录：
  - 遍历 `analysis_group`（参与分析的 Info 列表）
  - 每条 Info 写入一条记录，包含 run_id、info_id、info_title、role、weight、quality_score

**文件：`info_aggregation/services/event_analysis/pipeline.py`**
- `analyze_event_sources()` 返回值中增加 `used_info_ids: list[int]` 字段
- `_parse_result()` 中，从 `chronological_items` 提取 info_id 列表

**文件：`info_aggregation/services/event_analysis/schemas.py`**
- `EventAnalysisResult` dataclass 新增 `used_info_ids: list[int]` 字段

**文件：`info_aggregation/api/__init__.py`**
- 新增 `GET /api/admin/events/{event_id}/analysis-sources` — 查询某事件的分析来源
- 新增 `GET /api/admin/events/{event_id}/analysis-runs` — 查询某事件的历次分析运行
- 返回格式示例：
  ```json
  {
    "event_id": 123,
    "runs": [
      {
        "run_id": 456,
        "created_at": "2026-05-10T10:00:00Z",
        "mode": "llm",
        "provider": "qwen",
        "quality_score": 82.5,
        "input_item_count": 8,
        "sources": [
          {
            "info_id": 1001,
            "title": "OpenAI 发布 GPT-5",
            "role": "primary",
            "weight": 95,
            "quality_score": 88
          },
          ...
        ]
      }
    ]
  }
  ```

#### 2.3.2 Go 层

**文件：`info-serve/internal/repository/admin_store.go`**
- `GetEventAnalysisRuns()` — 查询事件的历次分析运行及来源

**文件：`info-serve/internal/transport/http/handler.go`**
- 新增路由：`GET /api/admin/events/:id/analysis-runs`
- 新增路由：`GET /api/admin/events/:id/analysis-sources`

#### 2.3.3 前端（info-admin）

**新增页面/组件：**
- `src/views/event/EventAnalysisDetail.vue` — 事件分析详情页（嵌入事件详情 Tab）
- 显示历次分析运行列表
- 点击运行 → 显示本次分析使用的所有信息源（标题、渠道、质量分、角色）

### 2.4 测试计划

| 测试项 | 验证点 |
|--------|--------|
| 溯源写入 | rebuild_events 后 → 查询 event_analysis_source 确认记录条数与 input_item_count 一致 |
| 溯源查询 | 调用 API → 返回的 sources 与入库记录一致 |
| 快照标题 | info 后续被删除 → sources 中仍保留 info_title 快照 |
| 多轮分析 | 同一事件多次 rebuild → 每轮产生独立 run，每轮的 sources 独立记录 |
| 字段完整 | sources 中 info_id、title、role、weight、quality_score 均正确 |

---

## 五、Phase 3 — 事件历史脉络分析

### 3.1 目标

在事件分析中引入历史上下文，使分析具备"前因后果"能力：
- 分析新批次数据时，查询同实体的历史事件和信息
- 生成事件演变趋势、前因摘要、影响范围扩展
- 构建完整时间线（从事件首次出现到现在的全脉络）

### 3.2 涉及的表变更

**表：event**（ALTER）

```sql
ALTER TABLE event
  ADD COLUMN previous_event_id INT DEFAULT NULL COMMENT '同实体前序事件ID',
  ADD COLUMN event_generation INT DEFAULT 1 COMMENT '事件代数(同类事件的迭代次数)',
  ADD COLUMN evolution_stage VARCHAR(20) DEFAULT 'emerging' COMMENT '演变阶段: emerging/peak/declining/resolved/recurring';
```

**新增表：event_evolution（事件演变记录表）**

```sql
CREATE TABLE event_evolution (
    id INT PRIMARY KEY AUTO_INCREMENT,
    event_id INT NOT NULL COMMENT '当前事件ID',
    previous_event_id INT DEFAULT NULL COMMENT '前序事件ID',
    evolution_type VARCHAR(30) DEFAULT '' COMMENT '演变类型: escalation/expansion/correction/recurrence/none',
    evolution_summary TEXT DEFAULT '' COMMENT '演变摘要: 本事件相比前序事件的增量变化',
    source_count_delta INT DEFAULT 0 COMMENT '来源数变化(正=增加)',
    key_change TEXT DEFAULT '' COMMENT '关键变化描述',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,

    INDEX idx_event_id (event_id),
    INDEX idx_previous_event_id (previous_event_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='事件演变记录表';
```

### 3.3 涉及的代码变更

#### 3.3.1 Python 层

**文件：`info_aggregation/database/models.py`**
- `Event` 模型新增字段：`previous_event_id`、`event_generation`、`evolution_stage`
- 新增 `EventEvolution` 模型

**文件：`info_aggregation/services/analysis/event_builder.py`**

重构 `rebuild_events()` 中对每个事件分组的处理逻辑：

```python
def _build_event_with_history(group, existing_events, session):
    """构建事件，包含历史脉络分析"""

    # 1. 查找同 core_entity 的历史事件
    core_entity = group[0].core_entity
    historical_events = _find_historical_events(core_entity, existing_events)

    # 2. 确定演变关系
    if historical_events:
        previous_event = historical_events[0]
        evolution = _analyze_evolution(group, previous_event, session)
        previous_event_id = previous_event.id
        event_generation = previous_event.event_generation + 1
    else:
        evolution = None
        previous_event_id = None
        event_generation = 1

    # 3. 查询历史信息构建完整时间线
    historical_infos = _query_historical_infos(core_entity, session, limit=50)

    # 4. 构建完整时间线（历史 + 当前）
    full_timeline = _build_full_timeline(historical_infos, group)

    # 5. 生成演变摘要
    evolution_summary = _generate_evolution_summary(evolution, group, historical_events)

    # 6. 确定演变阶段
    evolution_stage = _determine_evolution_stage(group, historical_events)

    return {
        'previous_event_id': previous_event_id,
        'event_generation': event_generation,
        'evolution_stage': evolution_stage,
        'evolution_summary': evolution_summary,
        'full_timeline': full_timeline,
        'historical_infos': historical_infos,
    }
```

新增方法：
- `_find_historical_events(core_entity, existing_events)` — 查找同实体的历史事件
- `_analyze_evolution(current_group, previous_event, session)` — 分析演变类型和关键变化
- `_query_historical_infos(core_entity, session, limit)` — 查询历史信息（用于时间线）
- `_build_full_timeline(historical_infos, current_group)` — 构建完整时间线
- `_generate_evolution_summary(evolution, current_group, historical_events)` — 生成演变摘要
- `_determine_evolution_stage(current_group, historical_events)` — 确定演变阶段

**文件：`info_aggregation/services/event_analysis/schemas.py`**

`EventAnalysisResult` 新增字段：
```python
@dataclass
class EventAnalysisResult:
    # ... 现有字段 ...
    previous_event_id: int = None  # 前序事件ID
    evolution_stage: str = "emerging"  # 演变阶段
    evolution_summary: str = ""  # 演变摘要
    full_timeline: list[TimelinePoint] = field(default_factory=list)  # 完整时间线
    history_context: str = ""  # 历史背景摘要
```

**文件：`info_aggregation/services/event_analysis/rule_provider.py`**

重构 `_build_*` 方法以接收历史上下文：
- `_build_what_happened()` — 加入历史演变信息
- `_build_why_it_matters()` — 加入历史影响范围对比
- 新增 `_build_history_context()` — 生成历史背景摘要
- 新增 `_build_evolution_summary()` — 生成演变摘要（替换现有 risk_notice 位置）

**文件：`info_aggregation/services/event_analysis/providers.py`**

修改 LLM 提示词，加入历史上下文：

```python
def _build_prompt(self, items, chronological_items=None, history_context=None) -> str:
    # ... 现有 source_blocks 构建 ...

    prompt = (
        "请基于真实来源生成事件分析，不要简单截取原文，不要编造没有证据的事实。\n"
        "输出JSON字段：one_line_summary, what_happened, why_it_matters, latest_update, "
        "heat_reason, source_compare, analysis_confidence, evolution_summary, history_context。\n"
        "每个字段必须是通顺中文完整句子。\n\n"
    )

    # 新增：加入历史背景（如果有）
    if history_context:
        prompt += f"【历史背景】\n{history_context}\n\n"

    prompt += "【当前来源】\n" + "\n".join(source_blocks)

    return prompt
```

`analyze()` 方法签名新增 `history_context` 参数。

**文件：`info_aggregation/services/event_analysis/pipeline.py`**

`analyze_event_sources()` 新增参数 `history_context`，传递给 rule 和 LLM provider。

**文件：`info_aggregation/api/__init__.py`**

`Event` 响应结构新增字段：`previous_event_id`、`event_generation`、`evolution_stage`、`evolution_summary`、`full_timeline`。

**文件：`info_aggregation/services/quality/data_quality.py`**

- `_find_historical_events()` 方法中，加入 event_generation > 1 的检测逻辑
- 新增检测：若同一 core_entity 短期内出现多个事件（generation > 1），标记为高价值追踪事件

#### 3.3.2 Go 层

**文件：`info-serve/internal/repository/event_store.go`**
- `ListEvents()` 返回中增加：`previous_event_id`、`event_generation`、`evolution_stage`
- `GetEventDetail()` 返回中增加：`evolution_summary`、`full_timeline`

### 3.4 演变阶段定义

| stage | 条件 | 说明 |
|-------|------|------|
| emerging | event_generation = 1 | 事件首次出现 |
| peak | 来源数 > 5 且 24h内有新来源加入 | 热度峰值 |
| escalating | event_generation > 1 且 source_count_delta > 3 | 持续升温/升级 |
| expanding | 来源渠道数 > 5 | 影响范围扩大 |
| declining | 48h无新来源且 generation > 1 | 热度消退 |
| resolved | 出现"结果"类关键词 | 事件终结 |
| recurring | event_generation > 3 | 反复出现 |

### 3.5 测试计划

| 测试项 | 验证点 |
|--------|--------|
| 历史事件关联 | 同 core_entity 出现第二次事件 → previous_event_id 正确关联 |
| 演变代数递增 | 每次新事件 → event_generation 递增 |
| 演变阶段判断 | 模拟峰值场景 → evolution_stage = "peak" |
| 演变摘要生成 | 有历史事件时 → evolution_summary 非空 |
| 完整时间线 | 有历史信息时 → full_timeline 包含历史节点 |
| 历史上下文写入 LLM | 有历史时 → prompt 包含 history_context |
| 演变记录表写入 | 每次事件构建 → event_evolution 表有记录 |

---

## 六、Phase 4 — 数据库瘦身

### 6.1 目标

清理废弃表、冗余字段，减少维护负担，避免代码与数据库不一致的困惑。

### 6.2 涉及变更

#### 6.2.1 删除废弃表

```sql
-- 确认无代码引用后执行
DROP TABLE IF EXISTS crawl_health_snapshot;
DROP TABLE IF EXISTS user_follow_keyword;
```

#### 6.2.2 合并冗余表

**方案 A：合并 event_timeline_analysis 到 event_timeline_entry**

```sql
ALTER TABLE event_timeline_entry
  ADD COLUMN run_id INT DEFAULT NULL COMMENT '关联分析运行ID',
  ADD COLUMN evidence JSON DEFAULT NULL COMMENT '证据JSON(分析增强时填充)';

-- Go 层：优先读取有 evidence 的行，fallback 到无 evidence 的行
-- Python 层：写入时同时写两表（兼容期）或只写 event_timeline_entry（完全迁移后）
```

**方案 B：清理 event_analysis_snapshot 冗余**

`event_analysis_snapshot` 与 `event_summary_snapshot` 数据完全重复。建议：
- 保留 `event_summary_snapshot`（Go 端读取）
- 标记 `event_analysis_snapshot` 为 Python 内部表，不再从 Go 端感知
- 或直接将 `event_analysis_snapshot` 的数据合并到 `event_summary_snapshot` 的 version 字段

**本计划选择方案 B**：保留 `event_summary_snapshot`，`event_analysis_snapshot` 改为 Python 内部调试表。

#### 6.2.3 代码清理

**文件：`info_aggregation/database/models.py`**
- 确认 `CrawlHealthSnapshot` 无代码引用后，移除模型定义
- `EventTimelineAnalysis` 保留（向后兼容），但代码中优先使用 `EventTimelineEntry`

**文件：`info-serve/internal/repository/`**
- 确认 `crawl_health_snapshot` 无 SQL 查询后移除

**文件：`info_aggregation/services/analysis/event_builder.py`**
- 保留写入 `EventTimelineAnalysis`（向后兼容），但后续可改为只写 `EventTimelineEntry`

### 6.3 实施步骤

1. **确认无引用**：搜索所有代码文件，确认 `crawl_health_snapshot`、`user_follow_keyword` 无任何引用
2. **删除 Python 模型**：`CrawlHealthSnapshot` 从 `models.py` 和 `database/__init__.py` 移除
3. **执行 DDL**：`DROP TABLE`
4. **验证**：运行测试套件，确认无报错

---

## 七、Phase 5 — 增量事件构建

### 7.1 目标

将 `rebuild_events()` 从全量重建改为增量更新：
- 只处理新增或变更的 Info
- 已有事件如有新 Info 加入，增量更新而非全量重建
- 消除 rebuild 期间的瞬态数据风险

### 7.2 核心设计

```
增量构建策略：
┌─────────────────────────────────────────────┐
│  1. 记录上次 rebuild 的 max_info_id 和 max_event_time    │
│     → 存储在新建表 rebuild_checkpoint              │
│                                             │
│  2. 增量查询：只取 id > max_info_id 的新 Info   │
│                                             │
│  3. 对每个新 Info：                            │
│     ├── 用 event_key 查找是否已存在事件           │
│     ├── 存在 → 增量追加 ItemLink，更新时间线/摘要   │
│     └── 不存在 → 新建事件，运行分析               │
│                                             │
│  4. 每日全量 rebuild 一次（清理孤儿数据、校准分数）│
└─────────────────────────────────────────────┘
```

### 7.3 涉及的表变更

**新增表：rebuild_checkpoint**

```sql
CREATE TABLE rebuild_checkpoint (
    id INT PRIMARY KEY AUTO_INCREMENT,
    checkpoint_type VARCHAR(30) DEFAULT 'incremental' COMMENT 'incremental / full',
    max_info_id_processed INT DEFAULT 0 COMMENT '已处理的最大InfoID',
    max_event_time_processed DATETIME DEFAULT NULL COMMENT '已处理的最大事件时间',
    events_created INT DEFAULT 0 COMMENT '本次新建事件数',
    events_updated INT DEFAULT 0 COMMENT '本次更新事件数',
    items_processed INT DEFAULT 0 COMMENT '本次处理Info数',
    started_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    finished_at DATETIME DEFAULT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='事件重建检查点';
```

### 7.4 涉及的代码变更

#### 7.4.1 Python 层

**文件：`info_aggregation/database/models.py`**
- 新增 `RebuildCheckpoint` 模型

**文件：`info_aggregation/services/analysis/event_builder.py`**

重构为两种模式：

```python
def rebuild_events(session, mode="incremental", limit=200):
    """
    mode: "incremental"  → 只处理新增Info，增量追加到现有事件
          "full"         → 全量重建（现有逻辑，清除后重建）
    """
    if mode == "full":
        _full_rebuild(session, limit)
    else:
        _incremental_rebuild(session)


def _incremental_rebuild(session):
    """增量重建：只处理新增Info"""

    # 1. 获取检查点
    checkpoint = _get_latest_checkpoint(session)

    # 2. 查询增量 Info
    new_infos = _query_new_infos(session, checkpoint)

    # 3. 对每个新 Info 进行事件归属
    for info in new_infos:
        _assign_to_event_incrementally(session, info, checkpoint)

    # 4. 对有新 Info 追加的事件，重新运行分析
    _re_analyze_events_with_new_items(session, checkpoint)

    # 5. 记录检查点
    _save_checkpoint(session, checkpoint)

    session.commit()


def _assign_to_event_incrementally(session, info, checkpoint):
    """将新 Info 增量追加到现有事件或新建事件"""

    event_key = _build_event_key(info)
    existing_event = _find_event_by_key(session, event_key)

    if existing_event:
        # 增量追加 ItemLink
        _append_item_link(session, existing_event, info)
        # 更新事件元数据（source_count、last_updated_at）
        _update_event_metadata(session, existing_event)
        # 标记需要重新分析
        checkpoint.add_event_to_reanalyze(existing_event.id)
    else:
        # 新建事件
        _create_event_incrementally(session, info, checkpoint)


def _re_analyze_events_with_new_items(session, checkpoint):
    """对有新增Info的事件重新运行分析"""

    events_to_reanalyze = checkpoint.get_events_to_reanalyze()

    for event in events_to_reanalyze:
        # 收集该事件的所有 Info（包括历史 + 新增）
        all_items = _collect_event_items(session, event)

        # 重新运行分析
        analysis = analyze_event_sources(all_items, all_items, session)

        # 更新事件摘要（只更新，不删除关联数据）
        _update_event_analysis(session, event, analysis)

        # 追加 AnalysisRun 记录
        _append_analysis_run(session, event, analysis)

        # 追加 AnalysisSource 记录
        _append_analysis_sources(session, event, all_items)
```

**文件：`info_aggregation/scheduler/__init__.py`**

- 修改调度策略：
  - 每10分钟运行一次增量 rebuild（`mode="incremental"`）
  - 每天凌晨3点运行一次全量 rebuild（`mode="full"`）
- 新增调度参数：`INCREMENTAL_REBUILD_ENABLED`（开关，默认 true）

**文件：`info_aggregation/api/__init__.py`**

- 修改 `POST /api/admin/rebuild-events` — 支持 `mode` 参数
  - `mode=full` → 全量重建
  - `mode=incremental` → 增量更新（默认）
- 新增 `GET /api/admin/rebuild-checkpoints` — 查询重建历史

### 7.5 兼容性和回滚

- 首次运行增量 rebuild 时，自动先执行一次全量 rebuild 建立基准
- 全量 rebuild 逻辑完全保留，支持随时手动触发
- 调度器故障恢复时，从上次检查点继续增量

### 7.6 测试计划

| 测试项 | 验证点 |
|--------|--------|
| 增量追加 | 新增 Info → 追加到现有事件，ItemLink 增加，source_count 更新 |
| 新事件创建 | 新 Info 无法归入现有事件 → 新建事件，运行分析 |
| 检查点记录 | 每次 rebuild → rebuild_checkpoint 有记录 |
| 增量分析 | 有新 Info 的事件 → 重新运行分析，Summary 更新 |
| 增量+全量混合 | 增量运行后 → 全量运行结果一致 |
| 故障恢复 | rebuild 中断 → 重启后从检查点恢复 |
| 历史数据不丢失 | 增量运行后 → 历史 ItemLink 保留，不被清除 |

---

## 八、风险评估与依赖关系

```
Phase 1 (Cookie)
    │
    ▼
Phase 2 (溯源) ─────────────────┐
    │                            │
    ▼                            │
Phase 3 (历史脉络)               │  (Phase 2/3 可并行开发，共享 schema 变更)
    │                            │
    ▼                            │
Phase 5 (增量构建) ◄────────────┘
    │
    ▼
Phase 4 (数据库瘦身) ────────── 可在任何阶段独立执行，但建议在 Phase 5 之后
```

| 风险点 | 影响 | 缓解措施 |
|--------|------|----------|
| Phase 3 对 event_builder 重构大 | 高 | 保留原有 `_rebuild_events` 逻辑，新增 `_build_event_with_history`，旧逻辑作为 `_full_rebuild` |
| 增量构建改变数据一致性假设 | 中 | 每日全量 rebuild 作为兜底，定期校验一致性 |
| Cookie 从 .env 迁移后 .env 仍有值 | 中 | 环境变量优先级高于数据库，渐进迁移 |
| Go 端需要同步读取新字段 | 中 | 新字段为可选，前端降级显示 |

---

## 九、验收标准

| 阶段 | 验收条件 |
|------|----------|
| Phase 1 | Cookie 可从管理端更新，爬虫可读取到新 Cookie，Cookie 过期可告警 |
| Phase 2 | 任意事件的任意分析运行，可追溯具体使用了哪些 Info |
| Phase 3 | 同一实体的新事件，显示前序事件、演变摘要、完整时间线 |
| Phase 4 | 数据库中无 dead code 表，Python 模型与数据库一致 |
| Phase 5 | 10分钟增量 rebuild 耗时 < 30秒，每日全量 rebuild 耗时 < 5分钟 |

---

## 十、后续规划（v1.2+）

以下改进不纳入本迭代，但应记录在案：

| 改进项 | 优先级 | 说明 |
|--------|--------|------|
| 语义聚类升级 | P1 | 从字符串匹配升级为向量嵌入相似度聚类 |
| 跨语言检测 | P1 | 引入翻译层，实现中英文事件的自动聚合 |
| Redis 缓存层 | P1 | 缓存首页事件列表、事件详情，降低数据库压力 |
| 全文搜索 | P1 | 引入 Elasticsearch/Meilisearch，替代 LIKE 查询 |
| LLM 提示词优化 | P2 | 加入 few-shot 示例、思维链引导 |
| 趋势预测 | P2 | 基于历史热度曲线预测事件峰值 |
| 知识图谱 | P3 | NER + 实体关系图，跨事件实体追踪 |
| 分布式爬取 | P3 | Celery + Redis，支持多实例水平扩展 |
