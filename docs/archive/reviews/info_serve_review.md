# info-serve 工程 Review 总结

## 1. 工程定位

**info-serve** 是整个 info-ai 体系的**核心 API 网关与业务中台**，基于 Go 语言构建，向上为 info-max（Web）、info-mvp（小程序/H5）、info-admin（管理后台）提供统一的数据接口，向下对接 MySQL 数据库。

核心职责：
- 用户侧：事件列表/详情、内容浏览、搜索、收藏、阅读历史
- 管理侧：渠道健康监控、采集调度、数据质量治理、事件重建
- 认证授权：JWT -based 用户认证 + Admin 角色权限
- 审计日志：管理操作全量审计

---

## 2. 系统架构

### 2.1 技术栈
- **Language**: Go 1.24.3
- **HTTP**: 标准库 `net/http`（无 Gin/Echo/Fiber 等框架）
- **Database**: MySQL（`database/sql` + `go-sql-driver/mysql`）
- **ORM**: 无（手写 SQL）
- **Auth**: JWT（自实现）
- **Config**: 环境变量 + `.env`
- **Testing**: 标准库 `testing` + 子包测试

### 2.2 模块结构
```
info-serve/
├── cmd/server/           # 主入口
├── cmd/create-admin/     # 管理员初始化工具
├── internal/
│   ├── app/              # 应用组装（依赖注入）
│   ├── config/           # 配置
│   ├── auth/             # 认证服务
│   ├── events/           # 事件业务逻辑
│   ├── content/          # 内容业务逻辑
│   ├── user/             # 用户服务（收藏/历史/偏好）
│   ├── admin/            # 管理服务
│   ├── audit/            # 审计服务
│   ├── repository/       # 数据访问层
│   ├── transport/http/   # HTTP 路由与 Handler
│   └── response/         # 统一响应封装
```

### 2.3 架构评价
**优点**：
- **Clean Architecture 雏形**：handler → service → repository 三层分离，职责清晰
- **依赖注入**：`app.go` 集中组装依赖，便于测试替换
- **零外部框架依赖**：仅依赖一个 MySQL driver，升级风险极低，编译产物小
- **统一响应格式**：`response.OK` / `response.BadRequest` 等封装规范
- **测试覆盖较好**：几乎每个子包都有 `*_test.go`，路由层测试完整

**问题**：
- **缺少 ORM/Query Builder**：手写 SQL 导致 `event_store.go` 出现 400+ 行大文件，存在拼接风险
- **无连接池配置**：`sql.Open` 后未配置 `SetMaxOpenConns` / `SetMaxIdleConns` / `SetConnMaxLifetime`
- **中间件链缺失**：CORS、日志、Recovery、限流等均为独立函数，未形成中间件链
- **无 OpenAPI/Swagger**：接口文档靠口头约定，前后端联调成本高
- **MySQL Error 3065 暴露**：`DISTINCT + ORDER BY` 未做兼容性处理，不同 SQL mode 下会崩溃

---

## 3. 代码逻辑

### 3.1 Handler 层 (`transport/http/`)
- 使用 Go 1.22+ 的 `http.HandleFunc("GET /path")` 路由语法，简洁现代
- 但参数解析、验证逻辑散落在各 Handler 中，未抽象为 middleware 或 binder
- `event_handler.go` 曾出现"错误被吞、日志不输出"的问题（后已修复）

### 3.2 Service 层 (`events/`, `content/`, `user/` 等)
- Service 层较薄，主要做参数校验和默认值填充
- `events.Service.ListEvents` 对分页、排序做了防御性处理（最大 50 条）
- 但缺少**缓存层**：每次列表查询都直透 MySQL，热点数据未做内存缓存

### 3.3 Repository 层 (`repository/`)
- `MySQLStore` 集中了所有 SQL，导致文件过大
- SQL 拼接使用字符串拼接（`+whereSQL+`），存在 SQL 注入风险（虽然 `buildEventWhere` 用了 `?` 占位符，但拼接模式本身是高风险习惯）
- `Scan` 时存在字段重复（`&item.LastUpdatedAt` 被 Scan 两次），虽不影响功能，但反映代码审查不足
- ` representativeInfoID` / `sourceBadges` / `eventTimeline` 等 N+1 查询问题：列表页每条事件都要额外 2-3 次查询

### 3.4 认证与授权
- JWT 自实现，secret 来自环境变量
- `RequireAdminWithAudit` middleware 将审计和权限校验耦合，虽合理但不可复用
- 未做 Token 刷新机制，用户 7 天后需重新登录

---

## 4. API 设计与产品化

### 4.1 RESTful 设计
- 版本控制：`/api` 和 `/api/v1` 同时注册，便于平滑迁移
- 资源命名规范：`/events`、`/me/favorites`、`/admin/channels`
- 但缺少**分页标准**：不同接口分页参数命名不一致（`page_size` vs `pageSize` 隐式问题）

### 4.2 管理 API
- 管理后台功能丰富：渠道健康、质量快照、详情任务重试、事件重建
- 但**缺少幂等设计**：`POST /admin/rebuild-events` 重复调用会重复执行
- **缺少异步反馈**：重建事件是耗时操作，但 API 是同步返回，大表时易超时

---

## 5. 问题汇总与优化方向

### 5.1 高优先级（近期）

| 问题 | 影响 | 优化方向 |
|------|------|----------|
| N+1 查询严重 | 列表页性能差，并发高时 DB 压力大 | 列表查询改为 JOIN 预加载，或引入本地缓存 |
| 无连接池配置 | 高并发下连接泄漏/耗尽 | 显式配置 `db.SetMaxOpenConns(25)` 等参数 |
| SQL 拼接模式 | 潜在 SQL 注入、维护困难 | 引入 `sqlx` 或 `squirrel` 作为 Query Builder |
| 无缓存层 | 热点数据重复查询 | Redis 缓存事件列表 + 详情，TTL 5-10 分钟 |
| 缺少中间件链 | 日志、Recovery、限流无法统一挂载 | 封装 `Middleware` 链式调用 |

### 5.2 中优先级（中期）

| 问题 | 影响 | 优化方向 |
|------|------|----------|
| 手写 SQL 维护成本高 | 新需求开发慢、易出错 | 在复杂查询处引入 `sqlx` + struct tag |
| 无 API 文档 | 联调成本高、新人 onboarding 慢 | 接入 `swaggo` 自动生成 Swagger |
| 审计日志仅记操作 | 无法追踪数据变更链路 | 审计日志增加变更前/后快照 |
| 管理操作同步阻塞 | 大表重建超时 | 引入异步任务表 + 进度查询接口 |
| 单点部署 | 无高可用 | Docker + Nginx 负载均衡 + DB 主从 |

### 5.3 低优先级（长期）

| 问题 | 影响 | 优化方向 |
|------|------|----------|
| 单体服务边界模糊 | 用户/管理/内容耦合 | 按领域拆分为微服务（用户服务、内容服务、管理服务） |
| 无链路追踪 | 分布式排查困难 | 接入 OpenTelemetry + Jaeger |
| 无限流熔断 | 突发流量可能打垮服务 | 引入 `golang.org/x/time/rate` 限流 + 健康检查 |

---

## 6. 总体评分

| 维度 | 评分 | 说明 |
|------|------|------|
| 架构设计 | 7/10 | 三层分离清晰，但缺少中间件和缓存层 |
| 代码质量 | 6.5/10 | 测试覆盖好，但 SQL 拼接和 N+1 是硬伤 |
| 可维护性 | 6/10 | 零框架依赖是双刃剑，开发效率偏低 |
| 性能优化 | 5/10 | 无缓存、无连接池优化、N+1 明显 |
| 安全性 | 6.5/10 | JWT 自实现无刷新，审计完整但缺少幂等 |
| 业务匹配 | 7.5/10 | 接口完整，管理功能丰富，支撑现有前端够用 |

**一句话总结**：info-serve 是一个"轻量、干净但偏原始"的 Go 服务，架构分层值得肯定，但**性能优化（缓存、N+1、连接池）**和**开发效率（Query Builder、Swagger）**是急需补齐的短板。
