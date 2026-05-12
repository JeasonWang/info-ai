# 信息达人数据库表结构文档

> 生成时间：2026-05-11 | 数据库：info-max (MySQL 8.x, utf8mb4)

## 一、ER 关系图

```
category ──1:N── channel ──1:N── crawl_task ──1:N── crawl_run_log
    │                  │
    │                  └──1:N── info
    │                          │
    └──1:N─────────────────────┤
                               │
    ┌──────────────────────────┘
    │
    ├──1:N── info_acquisition_log     (详情采集日志)
    ├──1:N── detail_job               (详情补偿任务)
    │
    └── 参与事件构建 ──┐
                        │
event ──1:N── event_item_link ──N:1── info  (事件↔信息 多对多)
    │
    ├──1:N── event_timeline_entry      (时间线节点)
    ├──1:N── event_summary_snapshot    (摘要快照，8种类型)
    │
    ├──1:N── event_analysis_run        (分析运行记录)
    │       ├──1:N── event_analysis_snapshot  (分析输出快照)
    │       ├──1:N── event_fact_snapshot      (事实+证据)
    │       └──1:N── event_timeline_analysis  (增强时间线)
    │
    └── 参与用户交互 ──┐
                        │
user_account ──1:N── user_session
               ├──1:N── user_favorite_event  (收藏事件)
               ├──1:N── user_preference      (偏好设置)
               ├──1:N── user_read_history    (阅读历史)
               └──1:N── admin_audit_log      (审计日志)

llm_model_config ──1:N── llm_call_log       (LLM调用日志)

data_quality_snapshot     (数据质量快照，独立表)
```

---

## 二、核心业务表（采集 → 事件 → 分析）

### 1. category — 分类表
| 字段 | 类型 | 说明 |
|------|------|------|
| id | INT PK | 分类ID |
| name | VARCHAR(50) UK | 分类名称（热点事件/经济数据/国际大事/科技动向/AI大模型/体育） |
| code | VARCHAR(50) UK | 分类编码（hot/economy/international/tech/ai/sports） |
| description | VARCHAR(200) | 描述 |

**用途**：Python+Go 双端读写。系统初始化时种子数据写入6个分类。

---

### 2. channel — 渠道表
| 字段 | 类型 | 说明 |
|------|------|------|
| id | INT PK | 渠道ID |
| name | VARCHAR(50) UK | 渠道名称（微博/头条/CSDN等） |
| code | VARCHAR(50) UK | 渠道编码 |
| base_url | VARCHAR(255) | 渠道基础URL |
| category_id | INT FK→category.id | 所属分类 |
| base_interval_minutes | INT | 基础采集间隔(分钟) |
| hot_interval_minutes | INT | 热点加速间隔(分钟) |
| min_interval_minutes | INT | 最小允许间隔 |
| max_interval_minutes | INT | 失败退避最大间隔 |
| manual_interval_enabled | INT | 是否启用人工配置 |
| effective_interval_minutes | INT | **当前实际生效间隔**（调度器使用此值） |
| schedule_version | INT | 配置版本号（热更新用） |
| is_active | INT | 是否启用 |

**用途**：Python+Go 双端读写。管理后台可配置调度间隔，调度器通过 schedule_version 感知变更。API 响应中的 `crawl_interval` 仅作为兼容字段，由 `base_interval_minutes` 推导。

**已落地优化**：
- 删除 `crawl_interval` 冗余字段
- 新增 `cookies TEXT` — 存储渠道采集Cookie凭证
- 新增 `extra_credentials JSON` — 扩展凭证（如知乎的 zse_93/zse_96）
- 新增 `credentials_updated_at DATETIME` — 凭证最后更新时间

**凭证格式**：
`mysql_migration_max.sql` 和 Python 初始化会为微博、知乎、小红书写入 `status=sample` 的格式样例，方便管理后台展示和后续手工替换。`CredentialProvider` 会忽略 `sample/placeholder/example` 状态的 Cookie 和 ZSE，只有管理后台保存后的 `status=active` 记录才会进入真实采集链路。

```json
{
  "cookie": "SUB=...; XSRF-TOKEN=...",
  "status": "active",
  "last_verified_at": "2026-05-12T16:30:00",
  "note": "可选备注"
}
```

知乎额外凭证放在 `extra_credentials`：

```json
{
  "zhihu": {
    "zse_93": "101_3_3.0",
    "zse_96": "2.0_...",
    "status": "active"
  }
}
```

---

### 3. info — 信息主表（核心表）
| 字段 | 类型 | 说明 |
|------|------|------|
| id | INT PK | 信息ID |
| title | VARCHAR(200) | 标题 |
| content | TEXT | 正文/详情 |
| category_id | INT FK→category.id | 分类 |
| channel_id | INT FK→channel.id | 渠道 |
| source_id | VARCHAR(100) | 来源唯一标识（去重用） |
| source_url | VARCHAR(500) | 来源URL |
| event_time | DATETIME | 事件发生时间 |
| core_entity | VARCHAR(100) | 核心主体/人物 |
| location | VARCHAR(100) | 地点 |
| indicator_name | VARCHAR(100) | 指标名称（经济类专用） |
| indicator_value | VARCHAR(100) | 指标数值（经济类专用） |
| detail_fetch_status | VARCHAR(20) | 详情状态：pending/list_only/partial/complete/failed |
| detail_fetch_error | VARCHAR(500) | 详情失败原因 |
| detail_strategy | VARCHAR(50) | 详情抓取策略 |
| detail_score | INT | 详情完整度得分(0-100) |
| detail_content_length | INT | 详情正文长度 |
| detail_fetched_at | DATETIME | 详情抓取完成时间 |
| tech_topic_type | VARCHAR(50) | 科技主题类型 |
| tech_entities | VARCHAR(500) | 科技核心实体（逗号分隔） |
| tech_keywords | VARCHAR(500) | 科技关键词（逗号分隔） |
| is_deleted | INT | 逻辑删除 0/1 |

**唯一约束**：`(source_id, channel_id)` — **这是爬取数据去重的核心机制**

**去重逻辑**：
1. **入库时硬去重**：爬虫采集后，通过 `(source_id, channel_id)` 唯一约束，相同来源不重复插入
2. **质量服务软去重**：`data_quality.py` 的 `find_duplicates()` 用标题相似度+同渠道+相近时间做模糊去重，`merge_duplicates()` 将重复项标记为 `is_deleted=1`
3. **事件构建时过滤**：`_is_low_quality_item()` 排除 `unusable` 级别和标题正文重复的条目

**用途**：Python写入+Go读取。系统最核心的表。

---

### 4. event — 事件主表
| 字段 | 类型 | 说明 |
|------|------|------|
| id | INT PK | 事件ID |
| event_key | VARCHAR(120) UK | **稳定键**：SHA1(category_id + 归一化锚点)，重建时复用 |
| title | VARCHAR(200) | 事件标题 |
| one_line_summary | VARCHAR(255) | 一句话摘要 |
| primary_category_id | INT FK→category.id | 主分类 |
| status | VARCHAR(20) | 状态：active/archived/hidden |
| heat_score | INT | 热度分 |
| freshness_score | INT | 时效分 |
| composite_score | INT | 综合分 |
| source_count | INT | 来源数 |
| started_at | DATETIME | 事件开始时间 |
| last_updated_at | DATETIME | 最后更新时间 |

**用途**：Python写入+Go读取。前端展示的核心对象。

---

### 5. event_item_link — 事件↔信息关联表
| 字段 | 类型 | 说明 |
|------|------|------|
| id | INT PK | 关联ID |
| event_id | INT FK→event.id | 事件ID |
| item_id | INT FK→info.id | 信息ID |
| role | VARCHAR(20) | 角色：primary/media/background |
| is_primary | INT | 是否主来源 |
| weight | INT | 权重(基于质量分) |

**唯一约束**：`(event_id, item_id)`

**关键问题**：此表记录了事件使用了哪些信息源，但**没有关联到具体的分析运行（event_analysis_run）**。每次 rebuild 全量删除重建，无法追溯某次分析具体用了哪些源。

---

## 三、事件分析相关表

### 6. event_analysis_run — 分析运行记录
| 字段 | 类型 | 说明 |
|------|------|------|
| id | INT PK | 运行ID |
| event_id | INT | 事件ID（逻辑FK，无真实外键约束） |
| analysis_version | VARCHAR(30) | 分析版本 |
| mode | VARCHAR(30) | 模式：rule/hybrid/llm |
| provider | VARCHAR(50) | 提供方 |
| model_name | VARCHAR(100) | 模型名称 |
| status | VARCHAR(20) | 运行状态 |
| input_item_count | INT | **输入来源数量**（有，但只记数量不记具体ID） |
| quality_score | FLOAT | 分析质量分 |
| confidence | FLOAT | 置信度 |
| fallback_used | INT | 是否规则回退 |
| failure_reason | VARCHAR(500) | 失败原因 |

**关键问题**：
- `input_item_count` 只记录了数量，**没有记录具体用了哪些 info.id**。无法回答"这次分析基于哪些爬取数据？"
- 使用逻辑FK而非真实FK，数据库层面无约束保障

**改进建议**：新增 `event_analysis_source` 关联表，记录每次分析使用的具体信息源：
```sql
CREATE TABLE event_analysis_source (
    id INT PRIMARY KEY AUTO_INCREMENT,
    run_id INT NOT NULL COMMENT '分析运行ID',
    info_id INT NOT NULL COMMENT '信息源ID',
    role VARCHAR(20) DEFAULT 'media' COMMENT '角色: primary/media',
    weight INT DEFAULT 0 COMMENT '权重',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_run_id (run_id),
    INDEX idx_info_id (info_id)
);
```

---

### 7. event_summary_snapshot — 事件摘要快照
| 字段 | 类型 | 说明 |
|------|------|------|
| event_id | INT FK→event.id | 事件ID |
| summary_type | VARCHAR(30) | 摘要类型（8种：one_line/what_happened/why_it_matters/latest_update/heat_reason/risk_notice/source_compare/analysis_confidence） |
| content | TEXT | 摘要内容 |
| version | INT | 版本号 |

**用途**：Python写入+Go读取。前端事件详情页展示的摘要内容来自此表。

---

### 8. event_timeline_entry — 事件时间线节点
| 字段 | 类型 | 说明 |
|------|------|------|
| event_id | INT FK→event.id | 事件ID |
| occurred_at | DATETIME | 发生时间 |
| summary | VARCHAR(255) | 节点摘要 |
| source_item_id | INT FK→info.id | 来源信息ID |
| confidence | FLOAT | 置信度 |
| display_order | INT | 展示顺序 |

**用途**：Python写入+Go读取。前端时间线展示。

---

### 9. event_analysis_snapshot — 分析输出快照
| 字段 | 类型 | 说明 |
|------|------|------|
| event_id | INT | 事件ID（逻辑FK） |
| run_id | INT | 分析运行ID（逻辑FK） |
| analysis_type | VARCHAR(50) | 分析类型 |
| content | TEXT | 分析内容 |
| provider | VARCHAR(50) | 提供方 |
| model_name | VARCHAR(100) | 模型名称 |
| quality_score | FLOAT | 质量分 |
| confidence | FLOAT | 置信度 |
| version | INT | 版本号 |

**用途**：仅Python读写，Go不读取。与 event_summary_snapshot 存在数据冗余。

---

### 10. event_fact_snapshot — 事实快照
| 字段 | 类型 | 说明 |
|------|------|------|
| event_id | INT | 事件ID（逻辑FK） |
| run_id | INT | 分析运行ID（逻辑FK） |
| fact_type | VARCHAR(50) | 事实类型 |
| content | TEXT | 事实内容 |
| source_item_id | INT | 来源信息ID（逻辑FK） |
| confidence | FLOAT | 置信度 |
| evidence | JSON | 证据JSON |

**用途**：仅Python读写。记录从来源中抽取的关键事实和证据链。

---

### 11. event_timeline_analysis — 增强时间线
| 字段 | 类型 | 说明 |
|------|------|------|
| event_id | INT | 事件ID（逻辑FK） |
| run_id | INT | 分析运行ID（逻辑FK） |
| occurred_at | DATETIME | 节点时间 |
| summary | VARCHAR(255) | 节点摘要 |
| source_item_id | INT | 来源信息ID |
| confidence | FLOAT | 置信度 |
| evidence | JSON | 证据JSON |
| display_order | INT | 展示顺序 |

**用途**：仅Python读写，Go不读取。与 event_timeline_entry **高度重叠**，区别仅在于多了 run_id 和 evidence 字段。

**改进建议**：合并到 event_timeline_entry，增加可选的 run_id 和 evidence 字段。Go端优先读取有 evidence 的增强版本。

---

## 四、采集运维表

### 12. info_acquisition_log — 详情采集日志
| 字段 | 类型 | 说明 |
|------|------|------|
| info_id | INT FK→info.id | 信息ID |
| channel_code | VARCHAR(50) | 渠道编码 |
| strategy | VARCHAR(50) | 详情策略 |
| status | VARCHAR(20) | 结果状态 |
| score | INT | 完整度得分 |
| content_length | INT | 正文长度 |
| failure_reason | VARCHAR(255) | 失败原因 |
| matched_rules | VARCHAR(500) | 命中规则 |
| raw_excerpt | TEXT | 内容摘要 |

**用途**：仅Python读写。记录详情抓取的每次执行结果。

---

### 13. detail_job — 详情补偿任务
| 字段 | 类型 | 说明 |
|------|------|------|
| info_id | INT FK→info.id | 信息ID |
| channel_code | VARCHAR(50) | 渠道编码 |
| status | VARCHAR(20) | pending/running/succeeded/failed/cancelled |
| priority | INT | 优先级（越大越优先） |
| attempt_count | INT | 已尝试次数 |
| max_attempts | INT | 最大尝试次数 |
| next_run_at | DATETIME | 下次执行时间 |
| last_failure_reason | VARCHAR(255) | 最近失败原因 |
| strategy_hint | VARCHAR(100) | 建议策略 |

**用途**：Python写入+Go读写。补偿队列，对低质量/失败/列表态内容进行二次抓取。

---

### 14. crawl_task — 采集任务
| 字段 | 类型 | 说明 |
|------|------|------|
| channel_id | INT FK→channel.id | 渠道ID |
| task_code | VARCHAR(80) UK | 任务编码 |
| task_name | VARCHAR(100) | 任务名称 |
| schedule_type | VARCHAR(20) | 调度类型：interval/manual/cron |
| schedule_value | VARCHAR(100) | 调度配置值 |
| schedule_version | INT | 已同步的配置版本 |
| status | VARCHAR(20) | active/paused/disabled |
| last_run_at | DATETIME | 最近运行时间 |
| next_run_at | DATETIME | 下次计划时间 |

**用途**：Python写入+Go读取。调度器管理的采集任务定义。

---

### 15. crawl_run_log — 采集运行日志
| 字段 | 类型 | 说明 |
|------|------|------|
| task_id | INT FK→crawl_task.id | 任务ID |
| channel_code | VARCHAR(50) | 渠道编码 |
| trigger_type | VARCHAR(20) | 触发方式：scheduler/manual/retry |
| status | VARCHAR(20) | success/partial/failed |
| raw_count | INT | 原始抓取数 |
| cleaned_count | INT | 清洗后数 |
| saved_count | INT | 入库数 |
| detail_success_count | INT | 详情成功数 |
| detail_failed_count | INT | 详情失败数 |
| error_message | VARCHAR(1000) | 错误信息 |

**用途**：Python写入+Go读取。管理后台的爬取运行记录和渠道健康指标来源。

---

### 16. crawl_health_snapshot — 历史表，已清理

`crawl_health_snapshot` 曾用于保存渠道健康快照，但当前 Go 管理后台已从 `crawl_run_log` 实时聚合成功率、详情完整率、最近成功/失败时间等指标。该表没有活跃代码读写，已从基准 schema 和 Python ORM 移除，历史库通过 `migration_v1.3.0_database_cleanup.sql` 删除。

---

### 17. data_quality_snapshot — 数据质量快照
| 字段 | 类型 | 说明 |
|------|------|------|
| category_code | VARCHAR(50) | 分类编码 |
| total_count | INT | 总内容数 |
| duplicate_title_count | INT | 重复标题数 |
| empty_content_count | INT | 正文为空数 |
| low_detail_score_count | INT | 低详情分数 |
| missing_entity_count | INT | 实体缺失数 |
| snapshot_payload | JSON | 完整报告JSON |

**用途**：Python写入+Go读取。管理后台数据质量页面展示。

---

## 五、LLM 相关表

### 18. llm_model_config — 大模型配置
| 字段 | 类型 | 说明 |
|------|------|------|
| provider_name | VARCHAR(50) | 供应商名称 |
| provider_code | VARCHAR(50) | 供应商编码 |
| base_url | VARCHAR(255) | API地址 |
| api_key | VARCHAR(500) | API密钥 |
| model_name | VARCHAR(100) | 模型名称 |
| is_enabled | INT | 是否启用 |
| daily_call_limit | INT | 每日调用上限 |
| daily_call_count | INT | 当日已调用次数 |
| priority | INT | 选择优先级（越小越优先） |
| consecutive_failure_count | INT | 连续失败次数（熔断用） |
| circuit_open_until | DATETIME | 熔断结束时间 |

**用途**：仅Python读写。管理后台通过Python API管理，Go不直接读取。

---

### 19. llm_call_log — LLM调用日志
| 字段 | 类型 | 说明 |
|------|------|------|
| config_id | INT | 模型配置ID（逻辑FK） |
| provider_code | VARCHAR(50) | 供应商编码 |
| model_name | VARCHAR(100) | 模型名称 |
| status | VARCHAR(20) | succeeded/failed |
| latency_ms | INT | 耗时毫秒 |
| input_item_count | INT | 输入来源数量 |
| error_message | VARCHAR(500) | 错误信息 |

**用途**：仅Python读写。LLM调用审计和熔断器状态跟踪。

---

## 六、用户相关表（Go独占，Python不读写）

### 20. user_account — 用户账号
### 21. user_session — 用户会话
### 22. user_favorite_event — 用户收藏事件
### 23. user_preference — 用户偏好
### 24. user_read_history — 阅读历史
### 25. admin_audit_log — 管理员审计日志
> `user_follow_keyword` 已在 v1.3.0 清理：功能未落地，Go/Python 均无读写引用。

---

## 七、可废弃/需简化的表和字段

| 对象 | 原因 | 建议 |
|------|------|------|
| `crawl_health_snapshot` 表 | 无活跃代码读写，Go端实时JOIN计算 | 删除或改为Go端写入 |
| `user_follow_keyword` 表 | SQL定义但代码未实现 | 删除，待功能实现时再建 |
| `channel.crawl_interval` 字段 | 被 base_interval_minutes/effective_interval_minutes 取代 | 删除 |
| `event_timeline_analysis` 表 | 与 event_timeline_entry 高度重叠 | 合并到 event_timeline_entry，增加 run_id/evidence 可选字段 |
| `event_analysis_snapshot` 表 | 与 event_summary_snapshot 数据冗余 | 考虑合并，或明确为Python内部表不暴露给Go |

**当前落地状态（2026-05-12）**：
- `channel.crawl_interval` 已从基准 schema 和 Go/Python 仓储查询中移除；API 返回的 `crawl_interval` 仅作为兼容字段，由 `base_interval_minutes` 推导。
- `crawl_health_snapshot`、`user_follow_keyword` 已从基准 schema 和 Python ORM 中移除；历史库通过 `migration_v1.3.0_database_cleanup.sql` 删除。
- `event_timeline_entry` 已新增 `run_id`、`evidence`，但 `event_timeline_analysis` 暂保留写入作为兼容表。
- 新增 `event_analysis_source`、`event_evolution`、`rebuild_checkpoint`，完整 schema 与分阶段迁移脚本保持一致。

---

## 八、事件分析完整处理流程

```
1. 爬虫采集 → Info 表（通过 source_id+channel_id 去重）
                    ↓
2. 详情抓取 → 更新 Info 的 detail_* 字段
                    ↓
3. 质量评估 → acquisition_quality_profile 标记 usable/unusable
                    ↓
4. 定时触发 rebuild_events()
   ├── incremental：按 rebuild_checkpoint 或已有关联最大 info_id 处理新增 Info
   ├── full：查询最近 limit 条 Info（默认200，按时间倒序）并重建当前窗口
   ├── 过滤低质量项（_is_low_quality_item）
   ├── 按 _build_event_key 分组
   │     ├── 优先使用 core_entity 作为锚点
   │     ├── 其次 tech_entities、tech_keywords
   │     └── 最后取标题前16字符（去除动作词）
   ├── full 模式清理当前事件关联、摘要、时间线、分析运行和来源追溯
   ├── **全量归档** Event.status = "archived"
   ├── 对每个分组：
   │     ├── 重建 Event（通过 event_key 复用已有ID）
   │     ├── 调用 analyze_event_sources() 进行分析
   │     │     ├── 规则分析（rule_provider.py）→ 7个摘要字段 + 时间线 + 事实
   │     │     └── LLM分析（providers.py）→ 同结构输出，失败回退规则
   │     ├── 写入 EventAnalysisRun（记录分析元信息）
   │     ├── 写入 EventAnalysisSource（记录本次分析具体使用的 info_id）
   │     ├── 写入 EventSummarySnapshot（8种摘要）
   │     ├── 写入 EventAnalysisSnapshot（8种分析输出，冗余）
   │     ├── 写入 EventFactSnapshot（事实+证据）
   │     ├── 写入 EventItemLink（事件↔信息关联）
   │     ├── 写入 EventTimelineEntry（时间线）
   │     └── 写入 EventTimelineAnalysis（兼容旧查询，后续可移除）
   └── commit
```

### 本地库检查与重建说明

本地默认连接：`127.0.0.1:3306/info-max`，账号 `root`，密码 `root1234`。

结构检查：
```bash
/usr/local/mysql-8.4.3-macos14-arm64/bin/mysql -uroot -proot1234 -h127.0.0.1 -P3306 -D info-max -e "SHOW COLUMNS FROM channel; SHOW TABLES LIKE 'event_analysis_source';"
```

迁移后如 `event_analysis_source` 为空，需要重建事件分析来源：
```bash
DB_TYPE=mysql DB_HOST=127.0.0.1 DB_PORT=3306 DB_USER=root DB_PASSWORD=root1234 DB_NAME=info-max \
  ./.venv/bin/python -c "from database import get_session; from services import rebuild_events; s=get_session(); rebuild_events(s, limit=200, mode='full'); s.close()"
```

### 关键问题总结

| # | 问题 | 影响 | 改进方向 |
|---|------|------|----------|
| 1 | **分析不记录来源明细**：EventAnalysisRun 只记 input_item_count，不记具体 info.id | 无法追溯"这次分析基于哪些数据" | 新增 event_analysis_source 关联表 |
| 2 | **全量重建**：每次 rebuild 删除所有关联数据重建 | 数据量大时O(n)且无检查点，瞬态故障可破坏所有事件数据 | 改为增量更新：只处理新增/变更的 Info |
| 3 | **聚类是字符串匹配**：锚点基于标题前16字符/实体CSV | 语义相同但措辞不同的信息无法聚合 | 引入向量嵌入相似度聚类 |
| 4 | **无历史事件对比**：分析时不查询同实体的历史事件 | 无法分析事件前因后果、演进趋势 | 分析时查询同 event_key 或同 core_entity 的历史 Event，生成对比/趋势分析 |
| 5 | **无跨语言检测**：路透社英文与中文渠道无法聚类 | 国际事件碎片化 | 引入翻译层或多语言嵌入 |
| 6 | **时间线无增量**：时间线仅来自当前批次的 Info | 无法展示事件的历史脉络 | 查询同事件历史 Info，构建完整时间线 |
| 7 | **Cookie存.env**：无法管理端更新，过期静默失败 | 运维需手动改.env重启 | Cookie存入 channel 表，管理端可更新 |
