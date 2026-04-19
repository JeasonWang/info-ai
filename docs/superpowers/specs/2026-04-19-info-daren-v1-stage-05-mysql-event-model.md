# 信息达人 V1 阶段文档 05：MySQL 最小事件模型设计

## 文档信息

- 项目名称：信息达人
- 阶段主题：MySQL 最小表结构、事件模型落地方式、平滑迁移方案
- 当前状态：已在对话中确认
- 更新时间：2026-04-19

## 1. 设计目标

在不破坏当前 demo 可运行性的前提下，为 `信息达人 MVP` 建立一套能够支撑事件流产品的最小 MySQL 模型。

设计需要同时满足：

- 尽快做出第一个能跑的版本
- 保持向完整事件系统平滑演进的能力

## 2. 总体迁移策略

MVP 阶段采用“保留旧内容层，新增事件层”的方式演进。

### 2.1 保留现有基础表

继续保留：

- `category`
- `channel`

它们可以直接作为产品的：

- 分类配置
- 来源配置

### 2.2 保留现有 `info` 作为内容层

MVP 阶段不建议立刻把当前 `info` 拆成 `raw_item + normalized_item` 两层。

原因：

- 当前 `info_aggregation` 已经围绕 `info` 可运行
- 如果首版强制彻底重构，会明显拖慢 MVP 落地
- `info` 可以先承担“标准化内容项”的角色

因此当前建议是：

- `info` 继续作为内容证据层的主表
- 后续再逐步演进为 `raw_item / normalized_item` 结构

## 3. `info` 表的演进方向

为了让 `info` 更适合事件系统，建议逐步补充以下字段：

- `published_at`
- `normalized_title`
- `normalized_content`
- `dedupe_key`
- `entities_json`
- `tags_json`
- `process_status`
- `event_binding_status`

这些字段的意义：

- `published_at`：统一内容发布时间
- `normalized_title`：标准化标题，便于聚类
- `normalized_content`：标准化文本内容，便于聚类和摘要
- `dedupe_key`：去重标识
- `entities_json`：实体抽取结果
- `tags_json`：标签候选
- `process_status`：处理流水线状态
- `event_binding_status`：事件绑定状态

## 4. MVP 新增的核心事件表

MVP 阶段建议新增 4 张核心表。

## 4.1 `event`

事件主表，是前端首页和详情页最终消费的核心对象。

建议字段：

- `id`
- `title`
- `one_line_summary`
- `primary_category_id`
- `status`
- `heat_score`
- `freshness_score`
- `composite_score`
- `source_count`
- `started_at`
- `last_updated_at`
- `created_at`
- `updated_at`

其中：

- `title`：事件主标题
- `one_line_summary`：首页展示的一句话看懂
- `primary_category_id`：主分类
- `status`：事件状态，例如 active / cooling / archived
- `heat_score`：热度分
- `freshness_score`：时效分
- `composite_score`：综合排序分
- `source_count`：事件包含的来源数量
- `started_at`：事件起始时间
- `last_updated_at`：最后一次事件更新时间

## 4.2 `event_item_link`

事件与内容项的关联表，用于把 `info` 里的内容绑定到具体事件。

建议字段：

- `id`
- `event_id`
- `item_id`
- `role`
- `is_primary`
- `weight`
- `created_at`

其中：

- `event_id`：关联事件
- `item_id`：关联内容项，当前阶段对应 `info.id`
- `role`：内容在事件中的角色
- `is_primary`：是否主来源
- `weight`：内容权重

建议 MVP 支持的 `role`：

- `primary`
- `media`
- `social`
- `background`

## 4.3 `event_timeline_entry`

事件时间线表，用于详情页时间线展示。

建议字段：

- `id`
- `event_id`
- `occurred_at`
- `summary`
- `source_item_id`
- `confidence`
- `display_order`
- `created_at`

其中：

- `occurred_at`：该节点发生时间
- `summary`：时间线节点文案
- `source_item_id`：该节点对应的来源内容项
- `confidence`：节点置信度
- `display_order`：手动或系统排序值

## 4.4 `event_summary_snapshot`

事件摘要快照表，用于保存不同类型的事件摘要。

建议字段：

- `id`
- `event_id`
- `summary_type`
- `content`
- `version`
- `created_at`

建议 MVP 支持的 `summary_type`：

- `one_line`
- `what_happened`
- `why_it_matters`
- `latest_update`

设计原因：

- 便于摘要版本管理
- 便于后续重算
- 便于人工修正
- 避免直接覆盖事件主表中的核心展示字段

## 5. 为什么这是适合 MVP 的最小模型

这套设计的核心优点在于“最小但不临时”。

### 5.1 首页查询简单

首页主要依赖：

- `event`

即可完成事件流展示。

### 5.2 详情查询清晰

详情页主要依赖：

- `event`
- `event_timeline_entry`
- `event_summary_snapshot`
- `event_item_link`

结构清晰，边界明确。

### 5.3 现有采集系统可复用

当前爬虫系统继续把内容落到 `info`，不需要一开始重写整个采集链。

### 5.4 为未来扩展保留空间

后续要扩展：

- 搜索
- 推荐
- 订阅
- 标签体系
- 人工运营
- 原始层 / 标准化层拆分

都可以在当前模型基础上平滑演进。

## 6. 建议索引方向

MVP 阶段建议优先建立以下索引。

### 6.1 `info`

- `unique(channel_id, source_id)`
- `index(category_id, published_at)`
- `index(dedupe_key)`

### 6.2 `event`

- `index(primary_category_id, composite_score, last_updated_at)`
- `index(status, last_updated_at)`

### 6.3 `event_item_link`

- `unique(event_id, item_id)`
- `index(item_id)`

### 6.4 `event_timeline_entry`

- `index(event_id, occurred_at)`

### 6.5 `event_summary_snapshot`

- `index(event_id, summary_type, version)`

## 7. 迁移原则

MVP 阶段建议遵循以下迁移原则：

1. 不推翻现有 `info_aggregation`
2. 先让 `info` 适应事件流水线
3. 先新增事件层
4. 新接口以 `event` 为中心
5. 老接口临时保留，支持过渡

## 8. 当前阶段结论

这一阶段确认了：

- MVP 不推翻现有 `info` 模型
- `info` 先作为内容证据层承接事件系统
- 新增 4 张核心事件表支撑首页与详情页
- MySQL 事件模型已经具备首版落地基础

## 9. 下一阶段待讨论主题

下一阶段建议进入：

- Redis 的最小职责设计
- 轻量异步机制设计
- Python / Go 服务边界演进
- 如何基于现有两个 demo 映射到新架构
