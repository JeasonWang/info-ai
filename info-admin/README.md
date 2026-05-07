# info-admin

`info-admin` 是信息达人 Pro 版本的独立 PC Web 管理后台，使用 Vue3 + TypeScript + Vite 构建。

## 职责边界

- 管理员登录。
- 采集监控。
- 数据质量查看。
- 手动触发采集、事件重建和质量治理动作。
- 分类管理。
- 渠道管理。
- 审计日志展示。

`info-admin` 只负责后台页面和交互，不直接连接数据库，不承载用户端能力，所有后台数据均来自 `info-serve`。

## 本地开发

```bash
cd /Users/jeasonwang/IdeaProjects/info-ai/info-admin
npm install
npm run dev
```

默认开发端口：`5174`。

## 环境变量

```text
VITE_API_BASE_URL=/api
```

未配置时默认使用同源请求。生产 Docker 会由 Nginx 将 `/api` 代理到 `info-serve:8085`；本地开发会由 Vite 代理到 `http://127.0.0.1:8085`。

后台业务接口统一请求 `info-serve` 的 `/api/v1/*` 路径；旧 `/api/*` 路径只作为服务端兼容入口保留。

当前管理动作通过 `info-serve` 统一鉴权和审计，再转发给 `info_aggregation` 执行：

- `POST /api/v1/admin/crawl-tasks/{channel_code}/trigger`
- `POST /api/v1/admin/rebuild-events`
- `POST /api/v1/admin/refresh-quality`
- `POST /api/v1/admin/archive-low-quality`
- `POST /api/v1/admin/archive-duplicate-titles`

## 测试和构建

```bash
cd /Users/jeasonwang/IdeaProjects/info-ai/info-admin
npm test -- --run
npm run build
```

## 编码规范

- 代码文件、目录、变量、类型、组件名使用英文。
- 页面展示文案使用中文。
- 关键业务注释使用中文。
- 新增页面必须接入路由守卫。
- 新增后台接口必须统一走 `src/services/httpClient.ts`。
- 新增后台接口路径必须通过 `src/services/apiPath.ts` 生成 `/api/v1/*` 路径。
