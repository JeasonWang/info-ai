# 信息达人事件流 MVP 接口说明

这份文档只补充当前 `事件理解器` MVP 新增的事件接口，原有 `info` 类接口继续保留。

## 1. 分类接口

### `GET /api/event-categories`

用于首页顶部分类入口。

示例响应：

```json
{
  "code": 0,
  "message": "success",
  "data": [
    { "code": "all", "name": "全网", "display_order": 0 },
    { "code": "tech", "name": "科技", "display_order": 1 },
    { "code": "economy", "name": "财经", "display_order": 2 },
    { "code": "sports", "name": "体育", "display_order": 3 },
    { "code": "international", "name": "国际", "display_order": 4 }
  ]
}
```

## 2. 事件流接口

### `GET /api/events`

用于首页事件流和分类频道页。

请求参数：

- `category_code`：默认 `all`
- `page`
- `page_size`

示例响应：

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "total": 12,
    "page": 1,
    "page_size": 10,
    "items": [
      {
        "id": 1,
        "title": "OpenAI 新模型能力引发全网讨论",
        "one_line_summary": "多个平台正在讨论 OpenAI 新模型发布带来的影响。",
        "primary_category": {
          "code": "tech",
          "name": "科技"
        },
        "heat_score": 95,
        "freshness_score": 88,
        "composite_score": 91,
        "last_updated_at": "2026-04-19 12:30:00",
        "source_count": 4,
        "source_badges": ["微博", "36氪", "路透"],
        "new_update_count": 3
      }
    ]
  }
}
```

## 3. 事件详情接口

### `GET /api/events/{event_id}`

用于事件详情页，第一屏优先服务 `时间线 + 事件解读`。

示例响应：

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "event": {
      "id": 1,
      "title": "OpenAI 新模型能力引发全网讨论",
      "one_line_summary": "一句话看懂这个热点事件。",
      "primary_category": {
        "code": "tech",
        "name": "科技"
      },
      "heat_score": 95,
      "last_updated_at": "2026-04-19 12:30:00"
    },
    "timeline": [
      {
        "id": 1,
        "occurred_at": "2026-04-19 09:00:00",
        "summary": "官方首次发布更新说明",
        "confidence": 0.96
      }
    ],
    "summaries": {
      "what_happened": "这是发生了什么的摘要。",
      "why_it_matters": "这件事为什么重要。",
      "latest_update": "最新进展已经出现。"
    },
    "source_views": [
      {
        "channel_name": "微博",
        "summary": "微博上出现了大量讨论。"
      }
    ],
    "representative_sources": [
      {
        "info_id": 11,
        "title": "路透原始报道",
        "channel_name": "路透",
        "source_url": "https://example.com/reuters",
        "event_time": "2026-04-19 12:00:00"
      }
    ]
  }
}
```

## 4. 手动重建接口

### `POST /api/admin/rebuild-events`

用于开发和调试阶段手动触发事件重建。

示例响应：

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "event_count": 8
  }
}
```

## 5. 当前实现说明

- 事件重建当前基于规则聚类
- 事件摘要和时间线当前来自事件重建服务的规则生成
- 原始内容层暂时继续复用 `info`
- 后续可以平滑演进到 `raw_item + normalized_item + event` 三层模型
