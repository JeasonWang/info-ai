# info-admin 管理后台架构设计

更新时间：2026-04-22

## 设计结论

`info-admin` 必须从当前静态原型升级为独立的 Vue3 + TypeScript 管理后台系统。现有 `管理后台.html`、`后台.js`、`样式.css` 只能作为页面信息结构参考，不能继续作为正式工程演进。

管理后台的定位是 PC Web 管理系统，面向管理员和运营人员，负责采集配置、采集监控、数据质量治理、审计日志查看等内部能力。它不承担用户侧展示，不与 `info-max` 混合部署，不使用中文代码文件名。

## 工程规范

### 技术栈

- Vue3。
- TypeScript。
- Vite。
- Vue Router。
- Vitest。
- vue-tsc。

第一阶段不引入复杂 UI 框架，先用自研轻量组件和清晰 CSS 变量保证可控性。后续如果后台表格、筛选、批量操作明显增多，再评估引入 Element Plus 或 Naive UI。

### 文件命名

所有代码目录、代码文件、变量、类型、组件名使用英文。

允许中文出现的位置：

- 页面展示文案。
- 测试用例名称中的业务说明。
- Markdown 文档。
- 必要的中文业务注释。

禁止中文出现的位置：

- `.ts`、`.vue`、`.css` 文件名。
- 路由 path。
- API 方法名。
- TypeScript 类型名。
- CSS class 命名。

## 推荐目录结构

```text
info-admin/
  package.json
  vite.config.ts
  tsconfig.json
  tsconfig.app.json
  tsconfig.node.json
  index.html
  README.md
  deploy.env.example
  src/
    main.ts
    App.vue
    router/
      index.ts
      guards.ts
    services/
      httpClient.ts
      authApi.ts
      adminApi.ts
    stores/
      authStore.ts
    types/
      auth.ts
      admin.ts
      api.ts
    layouts/
      AdminLayout.vue
      AuthLayout.vue
    views/
      LoginView.vue
      DashboardView.vue
      CrawlRunsView.vue
      DataQualityView.vue
      CategoriesView.vue
      ChannelsView.vue
      AuditLogsView.vue
    components/
      AppSidebar.vue
      AppTopbar.vue
      MetricCard.vue
      DataPanel.vue
      EmptyState.vue
      StatusBadge.vue
    styles/
      variables.css
      base.css
```

## 页面规划

### 登录页

路径：`/login`

能力：

- 管理员邮箱登录。
- 登录失败提示。
- 登录成功后保存 token 并跳转总览页。
- 已登录访问登录页时跳转 `/dashboard`。

### 总览页

路径：`/dashboard`

能力：

- 展示渠道数、事件数、信息数。
- 展示重复标题、正文缺失、实体缺失、低详情评分。
- 展示最近采集运行摘要。
- 明确提示当前后台连接的 `info-serve` 地址。

### 采集监控

路径：`/crawl-runs`

能力：

- 展示采集运行日志。
- 展示渠道编码、状态、原始数量、清洗数量、入库数量、详情成功和失败数量。
- 支持按状态和渠道筛选，第一阶段可以先做前端本地筛选。

### 数据质量

路径：`/data-quality`

能力：

- 展示质量快照。
- 展示重复标题、正文缺失、实体缺失、低详情评分。
- 后续扩展低质量数据列表、归档和重采入口。

### 分类管理

路径：`/categories`

能力：

- 展示分类列表。
- 新增分类。
- 编辑分类名称、编码和描述。
- 禁止在前端删除分类，避免误删导致采集和事件数据断链。

### 渠道管理

路径：`/channels`

能力：

- 展示渠道列表。
- 新增渠道。
- 编辑渠道名称、编码、基础 URL、分类、采集间隔、启停状态。
- 渠道编码是爬虫注册和采集任务绑定的关键字段，修改时要有明确风险提示。

### 审计日志

路径：`/audit-logs`

能力：

- 展示管理员操作记录。
- 展示管理员 ID、动作、目标类型、目标 ID、IP、时间。
- 第一阶段只读，不支持删除审计记录。

## 接口边界

`info-admin` 只调用 `info-serve`。

环境变量：

```text
VITE_INFO_SERVE_BASE_URL=http://localhost:8080
```

统一 HTTP 客户端负责：

- 自动拼接 base URL。
- 自动注入 `Authorization: Bearer <token>`。
- 统一解析 `{ code, message, data }`。
- 401 或 403 时清理登录态并跳转登录页。
- 网络异常时返回可读错误。

## 登录态设计

第一阶段使用 localStorage 保存 token，key 为：

```text
info-admin-token
```

后续如果进入生产部署，再评估 HttpOnly Cookie 或服务端 session cookie，降低 XSS 后 token 泄露风险。

## 测试策略

### 单元测试

- `httpClient`：验证 token 注入、错误解析、未授权处理。
- `authStore`：验证登录态保存、读取、清理。
- `router guards`：验证未登录跳转登录页，已登录不能访问登录页。

### 组件测试

- 登录页提交成功后跳转。
- 总览页能渲染指标。
- 分类管理页能新增分类并刷新列表。
- 渠道管理页能新增渠道并刷新列表。

### 构建验证

每次提交前必须运行：

```bash
cd /Users/jeasonwang/IdeaProjects/info-ai/info-admin
npm test -- --run
npm run build
```

## 迁移策略

第一阶段迁移不保留旧静态文件。

执行步骤：

1. 删除旧的 `管理后台.html`、`后台.js`、`样式.css`。
2. 初始化 Vue3 + TypeScript + Vite 工程。
3. 迁移现有页面信息结构到 Vue 页面。
4. 接入 `info-serve` 管理 API。
5. 补测试和构建验证。
6. 更新 README 和部署说明。

## 完成标准

- `info-admin` 可以独立安装依赖、运行、构建、部署。
- 全部代码文件使用英文命名。
- 登录、总览、采集监控、数据质量、分类管理、渠道管理可用。
- 后台接口全部来自 `info-serve`。
- 用户端 `info-max` 不包含管理配置功能。
- 测试和构建通过。
