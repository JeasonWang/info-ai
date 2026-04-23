# 信息达人前端

`info-max` 是信息达人的 Web/H5 前端，当前已经切到 `事件理解器` 的 MVP 形态。

## 当前能力

- 首页事件流：默认展示全网热点事件
- 分类切换：支持 `全网 / 科技 / 财经 / 体育 / 国际`
- 一句话看懂：每条事件卡片展示极短摘要
- 事件详情页：展示事件时间线、事件解读、多平台观点、代表性原始来源
- 单元测试：覆盖首页、分类 tabs、事件卡片、时间线、事件详情

## 当前接口

- 事件相关接口已切换到 `info-serve`：
  - `GET /api/v1/event-categories`
  - `GET /api/v1/events`
  - `GET /api/v1/events/{id}`
- 兼容保留旧接口：
  - `GET /api/categories`
  - `GET /api/channels`
  - `GET /api/infos`
  - `GET /api/infos/{id}`
  - `GET /api/stats`
  - `POST /api/crawl/trigger`

## 本地启动

1. 启动采集侧旧后端 `info_aggregation`，默认地址为 `http://localhost:8000`
2. 启动 Go API 服务 `info-serve`，默认地址为 `http://localhost:8080`
3. 在当前目录安装依赖并启动前端

```bash
npm install
npm run dev
```

如需自定义后端地址，请在 `.env` 中设置：

```bash
VITE_API_BASE_URL=http://localhost:8000
VITE_INFO_SERVE_BASE_URL=http://localhost:8080
```

## 测试与构建

```bash
npm test
npm run build
```

## 目录说明

```text
info-max/
├─ src/
│  ├─ components/    # 事件流、时间线、摘要面板等组件
│  ├─ services/      # 后端 API 请求封装
│  ├─ views/         # 首页、事件详情页、配置页
│  ├─ router.ts      # 路由
│  ├─ styles.css     # 样式系统
│  ├─ types.ts       # 类型定义
│  └─ utils.ts       # 时间和内容工具方法
├─ vitest.config.ts
├─ package.json
└─ README.md
```

## 下一步建议

- 增加事件详情页的相关推荐和事件状态
- 接入 `/api/admin/rebuild-events` 的管理入口
- 继续补搜索、订阅、个性化推荐等后续版本能力
