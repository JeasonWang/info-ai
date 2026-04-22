# info-admin

`info-admin` 是信息达人 Pro 版本新增的 PC Web 管理与监控后台。

当前阶段先提供静态骨架，用于确认后台信息架构和视觉方向；后续会接入 `info-serve` 的管理 API，并要求管理员登录后才能访问真实数据。

## 当前页面

- `管理后台.html`：管理后台入口页面。
- `样式.css`：PC Web 优先的视觉样式。
- `后台.js`：页面交互与接口占位。

## 后续接入

- 登录接口：`POST /api/auth/login`
- 当前用户：`GET /api/me`
- 管理探活：`GET /api/admin/health`
- 采集任务：待接入 `info-serve` 管理 API
- 数据质量：待接入 `info-serve` 管理 API
