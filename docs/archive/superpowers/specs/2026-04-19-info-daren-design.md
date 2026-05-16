# 信息达人产品与系统设计总文档

## 文档信息

- 项目名称：信息达人
- 文档类型：产品设计 + 系统设计总文档
- 当前阶段：设计已确认，可进入实施规划
- 更新时间：2026-04-19

## 1. 产品定位

`信息达人` 的目标不是做一个简单的信息聚合器，而是做一个面向大众热点用户的 `事件理解器`。

产品核心价值：

- 用 `事件聚合` 替代多平台切换
- 用 `一句话看懂` 帮用户快速理解热点
- 用 `事件时间线` 帮用户理解事情的发展过程
- 用 `多来源归纳 + 背景补充` 降低用户的信息理解成本

一句话定义：

`信息达人是一个面向大众用户的事件理解器，用事件聚合替代平台切换，用一句话摘要和时间线帮助用户更快看懂全网热点。`

## 2. 用户与场景

### 2.1 目标用户

- 大众热点用户

### 2.2 核心场景

- 刷热点但不想切平台

### 2.3 关键产品选择

- 首页优先强调：`一句话看懂`
- 详情页优先强调：`事件时间线`
- 排序策略：`热度 + 时效混合`
- 首页结构：`综合流 + 分类入口`

### 2.4 MVP 默认分类

- 全网
- 科技
- 财经
- 体育
- 国际

## 3. 产品路线

最终选择的路线是：

`以智能热榜型为主，吸收一部分多源解读型能力`

这意味着：

- 首页负责“快”
- 详情页负责“懂”
- 第一版优先证明事件流产品价值
- 后续再逐步增强推荐、搜索、订阅和多端能力

## 4. MVP 范围

### 4.1 必做能力

- 首页事件流
- 顶部分类切换
- 事件卡片展示
- 一句话看懂
- 事件详情页
- 事件时间线
- 多来源归纳
- 背景补充
- 代表性来源列表
- 热度 + 时效混合排序
- 少量高价值来源接入
- 简单管理能力

### 4.2 暂不纳入 MVP

- 个性化推荐
- 评论社区
- 复杂搜索
- 完整运营后台
- 全量终端一次性覆盖
- 深度研报式分析

### 4.3 MVP 路线

采用 `极简闭环型`：

`打开首页 → 刷到事件 → 一句话看懂 → 点进详情 → 看时间线 → 查看来源`

## 5. 系统设计原则

### 5.1 采集层与理解层分离

- 采集负责获取内容
- 理解层负责事件聚类、摘要、时间线、背景补充

### 5.2 以事件为中心

- 原始内容是证据材料
- 事件才是用户真正消费的主对象

### 5.3 处理链可插拔

以下能力独立设计为处理器：

- 标准化
- 去重
- 聚类
- 事件合并
- 摘要生成
- 时间线生成
- 评分排序

### 5.4 前后端解耦

- 前端面向 `event API`
- 后端底层采集逻辑可持续演进

### 5.5 MVP 可快落地，架构不能一次性

- 首版只做最短闭环
- 但边界、模型、异步处理链按长期平台方向设计

## 6. 分层架构

### 6.1 数据采集层

负责：

- 爬虫采集
- API 拉取
- 外部源接入

### 6.2 数据标准化层

负责：

- 清洗
- 去重
- 字段统一
- 标签与实体候选提取

### 6.3 事件理解层

负责：

- 事件聚类
- 事件合并 / 新建
- 一句话摘要
- 背景补充
- 时间线整理
- 热度与时效评分

### 6.4 服务输出层

负责：

- 首页事件流 API
- 事件详情 API
- 分类 API
- 管理接口

### 6.5 应用交互层

负责：

- Web / H5
- 后续扩展到 uni-app 小程序 / 多端

## 7. 技术栈与职责分工

### 7.1 Python

MVP 主力语言，负责：

- 爬虫采集
- 数据标准化
- 事件聚类
- 摘要与时间线生成
- 事件 API

### 7.2 Go

后续增长阶段引入，优先用于：

- 高并发网关
- 高吞吐读服务
- 实时服务

### 7.3 MySQL

权威数据源，负责：

- 分类与渠道配置
- 内容证据层
- 事件主表
- 时间线
- 摘要快照

### 7.4 Redis

辅助层，负责：

- 首页事件流缓存
- 事件详情缓存
- 分布式锁
- 去重辅助
- 任务状态辅助

### 7.5 MQ

先设计位置，后逐步增强，负责：

- 标准化任务分发
- 聚类任务触发
- 摘要和时间线生成任务触发
- 重算任务触发

当前策略：

- MVP 不强制引入重型 MQ
- 先把异步接口与任务边界设计清楚

### 7.6 Vue3

MVP Web / H5 主前端技术

### 7.7 uni-app

后续多端和小程序扩展技术

## 8. 事件理解流水线

建议的总体处理链：

`raw content / info → 标准化 → 去重 → 候选聚类 → 事件合并 / 新建 → 摘要生成 → 时间线生成 → 评分发布`

### 8.1 采集入库

- 来源内容进入内容层
- 保留原始字段和来源信息

### 8.2 标准化与去重

- 统一标题、摘要、时间、来源、标签候选
- 去除明显重复项

### 8.3 事件候选识别

- 基于时间窗口、关键词、实体和分类做初步聚类

### 8.4 事件合并 / 新建

- 归并到已有事件或创建新事件

### 8.5 事件理解生成

输出：

- one_line
- what_happened
- why_it_matters
- latest_update

### 8.6 时间线提取

- 抽取 3 到 8 个关键节点
- 按时间顺序输出

### 8.7 评分与发布

- heat_score
- freshness_score
- source_diversity_score
- composite_score

## 9. MySQL 最小模型

### 9.1 保留现有基础表

- `category`
- `channel`

### 9.2 保留 `info` 作为 MVP 内容层

MVP 阶段先不强制拆成 `raw_item + normalized_item`，而是在现有 `info` 基础上平滑演进。

建议逐步补充字段：

- `published_at`
- `normalized_title`
- `normalized_content`
- `dedupe_key`
- `entities_json`
- `tags_json`
- `process_status`
- `event_binding_status`

### 9.3 新增核心事件表

#### `event`

核心字段：

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

#### `event_item_link`

核心字段：

- `event_id`
- `item_id`
- `role`
- `is_primary`
- `weight`

#### `event_timeline_entry`

核心字段：

- `event_id`
- `occurred_at`
- `summary`
- `source_item_id`
- `confidence`
- `display_order`

#### `event_summary_snapshot`

核心字段：

- `event_id`
- `summary_type`
- `content`
- `version`

`summary_type` MVP 先支持：

- `one_line`
- `what_happened`
- `why_it_matters`
- `latest_update`

## 10. MVP API 设计

### 10.1 首页事件流 API

`GET /api/events`

请求参数：

- `category_code`
- `page`
- `page_size`
- `sort`

返回字段建议：

- `id`
- `title`
- `one_line_summary`
- `primary_category`
- `heat_score`
- `freshness_score`
- `composite_score`
- `last_updated_at`
- `source_count`
- `source_badges`
- `new_update_count`

### 10.2 事件详情 API

`GET /api/events/{event_id}`

返回建议包含：

- `event`
- `timeline`
- `summaries`
- `source_views`
- `representative_sources`

### 10.3 分类 API

`GET /api/event-categories`

返回建议包含：

- `name`
- `code`
- `icon`
- `display_order`

## 11. Redis 与轻量异步策略

### 11.1 Redis 最小职责

- 首页事件流缓存
- 热门事件详情缓存
- 分布式锁
- 去重辅助键

### 11.2 MVP 轻量异步

MVP 阶段建议：

- 保留异步处理链设计
- 不强制上重型 MQ
- 先用轻量方式完成任务分发和重试

任务边界建议预留：

- 标准化任务
- 聚类任务
- 摘要任务
- 时间线任务
- 重算任务

## 12. 基于现有 demo 的改造方向

### 12.1 `info_aggregation`

先改造成：

- 继续采集内容到 `info`
- 新增事件模型
- 新增事件处理链
- 新增事件 API

### 12.2 `info-max`

先改造成：

- 首页消费 `/api/events`
- 详情消费 `/api/events/{id}`
- 顶部分类消费 `/api/event-categories`

## 13. 版本路线

### M0

- 加事件模型和事件 API 骨架
- 不破坏现有 demo

### M1

- 跑通首个可运行 MVP
- 完成事件流和时间线详情

### M2

- 优化聚类、摘要、时间线
- 增加更多来源和频道

### M3

- 搜索
- 订阅
- 推荐
- 运营能力
- 多端扩展

## 14. 当前结论

到目前为止，`信息达人` 的设计方向已经明确：

- 长期目标是做全面的事件理解平台
- 短期目标是尽快做出一个能运行的 MVP
- MVP 以事件流和时间线详情为核心
- 技术架构优先保证快速落地与长期演进兼容

## 15. 相关阶段文档

- [阶段 01：产品基础与系统骨架](/D:/ai-coding/docs/superpowers/specs/2026-04-19-info-daren-v1-stage-01-foundation.md)
- [阶段 02：事件理解流水线](/D:/ai-coding/docs/superpowers/specs/2026-04-19-info-daren-v1-stage-02-event-pipeline.md)
- [阶段 03：MVP 范围与版本路线](/D:/ai-coding/docs/superpowers/specs/2026-04-19-info-daren-v1-stage-03-mvp-scope.md)
- [阶段 04：MVP API 设计与技术架构基线](/D:/ai-coding/docs/superpowers/specs/2026-04-19-info-daren-v1-stage-04-api-and-tech-baseline.md)
- [阶段 05：MySQL 最小事件模型](/D:/ai-coding/docs/superpowers/specs/2026-04-19-info-daren-v1-stage-05-mysql-event-model.md)
