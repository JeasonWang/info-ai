# info-serve 服务架构设计

更新时间：2026-04-22

## 设计结论

`info-serve` 是信息达人 Pro 版本的业务 API 服务，负责用户端 API、管理后台 API、用户鉴权、权限控制、审计、业务查询和后续个性化能力。它不能演变成随手堆 handler 和 SQL 的薄接口服务，必须提前确立稳定的 Go 分层架构。

当前 `info-serve` 已经具备雏形：`cmd`、`internal/auth`、`internal/admin`、`internal/events`、`internal/repository`、`internal/router` 等目录已经存在。下一阶段不是推倒重写，而是在现有代码上逐步收敛到清晰边界。

## 架构原则

- Handler 只处理 HTTP 协议，不写业务规则。
- Service 处理业务用例、参数规则、权限语义和跨仓储编排。
- Repository 只处理 SQL、事务和数据映射。
- Domain 保存稳定业务模型、枚举和领域错误。
- Middleware 处理横切能力，例如鉴权、审计、CORS、日志、恢复。
- Response 统一 API 返回结构，不在各 handler 中散落 JSON 格式。
- Config 和 Database 必须独立，启动装配不能散落在 `cmd/server/main.go`。
- 所有新接口先写测试，再写实现。
- 所有数据库结构变更必须先写 SQL 文件，字段必须带中文注释。

## 推荐目录结构

```text
info-serve/
  cmd/
    server/
      main.go
    create-admin/
      main.go
  internal/
    app/
      app.go
      dependencies.go
    config/
      config.go
    database/
      mysql.go
    domain/
      admin.go
      audit.go
      auth.go
      event.go
      errors.go
    service/
      admin_service.go
      audit_service.go
      auth_service.go
      event_service.go
    repository/
      mysql_store.go
      admin_repository.go
      audit_repository.go
      auth_repository.go
      event_repository.go
    transport/
      http/
        router.go
        middleware/
          auth.go
          audit.go
          cors.go
        handler/
          admin_handler.go
          auth_handler.go
          event_handler.go
          health_handler.go
    response/
      response.go
  migrations/
    20260422_0001_pro_schema.sql
  docs/
    api.md
  deploy.env.example
  README.md
```

说明：可以分阶段迁移，短期允许保留现有 `internal/admin`、`internal/auth`、`internal/events` 包。HTTP 路由入口、健康检查和鉴权 handler 已经迁入 `internal/transport/http`，后续新增 HTTP 代码必须进入该目录；现有事件和管理 handler 会继续小步迁移。

## 分层职责

### cmd

只负责进程入口。

允许：

- 读取配置。
- 初始化 app。
- 启动 HTTP server。
- 处理关闭信号。

不允许：

- 写路由细节。
- 写 SQL。
- 写业务逻辑。

### app

负责依赖装配。

职责：

- 初始化配置。
- 初始化 MySQL。
- 初始化 repository。
- 初始化 service。
- 初始化 HTTP router。

这样可以避免 `main.go` 越来越胖，也方便测试时替换依赖。

### domain

负责稳定业务概念。

内容：

- 用户、会话、事件、分类、渠道、审计日志等模型。
- 领域错误，例如 `ErrInvalidInput`、`ErrNotFound`、`ErrDuplicated`。
- 稳定枚举，例如角色、渠道状态、采集状态。

原则：domain 不依赖 repository、service、handler。

### service

负责业务用例。

例子：

- `AuthService.Register`
- `AuthService.Login`
- `AdminService.CreateChannel`
- `EventService.ListEvents`
- `AuditService.Record`

Service 可以依赖 repository 接口，不依赖 MySQL 具体实现，不依赖 HTTP。

### repository

负责 MySQL 数据访问。

原则：

- SQL 集中在 repository。
- 每个方法只做数据访问和映射。
- 复杂写入必须使用事务。
- MySQL 错误要转换为领域错误。
- 不在 repository 里做权限判断。

### transport/http

负责 HTTP 入站协议。

内容：

- Router。
- Handler。
- Middleware。

Handler 职责：

- 解析 path、query、body。
- 调用 service。
- 把 service 错误转换为 HTTP 响应。
- 不写 SQL。
- 不做复杂业务判断。

## API 规范

### 路径

当前第一阶段可以继续使用：

```text
/api/auth/*
/api/events
/api/admin/*
```

后续进入稳定版本前，建议统一升级为：

```text
/api/v1/auth/*
/api/v1/events
/api/v1/admin/*
```

升级时需要兼容旧路径一个版本周期。

### 响应结构

统一返回：

```json
{
  "code": 0,
  "message": "success",
  "data": {}
}
```

错误返回：

```json
{
  "code": 400,
  "message": "参数不合法"
}
```

### 错误映射

- `ErrInvalidInput` -> 400。
- `ErrInvalidCredentials` -> 401。
- `ErrUnauthorized` -> 401。
- `ErrForbidden` -> 403。
- `ErrNotFound` -> 404。
- `ErrDuplicated` -> 409。
- 未知错误 -> 500，并写日志。

当前 `response` 包需要补充 `NotFound` 和 `InternalServerError`，避免所有错误都落到 400。

## 鉴权与权限

### 用户侧

未登录可以访问：

- 分类列表。
- 事件列表。
- 事件详情。
- 搜索。

登录后可以访问：

- 收藏。
- 关注关键词。
- 阅读历史。
- 服务端筛选偏好。

### 管理侧

所有 `/api/admin/*` 必须要求管理员或运营角色。

管理接口必须写审计日志，审计内容包括：

- 管理员 ID。
- 动作。
- 目标类型。
- 目标 ID。
- 请求 IP。
- 创建时间。

## 数据库与迁移规范

MySQL 是 Pro 版本唯一主库。

规范：

- 建表 SQL 必须保存在 `info_aggregation/sql` 或 `info-serve/migrations`。
- 所有字段必须有中文 `COMMENT`。
- 索引必须明确命名。
- 外键是否使用要按写入频率和数据一致性权衡，但必须在设计文档中说明。
- 不允许只在本地手工改库，不保存迁移脚本。

## 测试规范

### 单元测试

每个 service 必须覆盖：

- 正常路径。
- 参数非法。
- 重复数据。
- 数据不存在。
- 权限不满足。

### 路由测试

每个新增 HTTP API 必须覆盖：

- 未登录。
- 普通用户访问管理接口。
- 管理员成功访问。
- 请求体非法。
- service 返回错误。

### Repository 测试

Repository 分两类：

- 默认 `go test ./...` 不依赖真实 MySQL。
- 使用 `INFO_SERVE_TEST_MYSQL_DSN` 时运行真实 MySQL 集成测试。

本地集成测试命令：

```bash
cd /Users/jeasonwang/IdeaProjects/info-ai/info-serve
GOCACHE=/tmp/info-serve-go-build-cache \
INFO_SERVE_TEST_MYSQL_DSN='root:root1234@tcp(127.0.0.1:3306)/info-max?charset=utf8mb4&parseTime=true&loc=Local' \
go test ./internal/repository -v
```

## 近期重构路线

### 第一阶段：架构守正

- 补充本设计文档。
- 更新 README，明确服务职责和目录规范。
- 新增 `internal/app`，把启动装配从 `cmd/server/main.go` 中抽离。
- 补充 `response.NotFound` 和 `response.InternalServerError`。

### 第二阶段：HTTP 层归位

- 新建 `internal/transport/http`。
- 将现有 `router`、`handler`、`middleware` 逐步迁移进去。
- 保持 API 行为不变。
- 迁移过程中每一步都跑路由测试。

### 第三阶段：领域模型归位

- 新建 `internal/domain`。
- 把跨模块共享模型和错误逐步迁移到 domain。
- 避免 `admin`、`auth`、`events` 包之间互相泄漏概念。

### 第四阶段：管理能力补齐

- 审计日志查询。
- 手动触发采集。
- 失败任务重试。
- 低质量数据治理入口。

## 完成标准

- `cmd/server/main.go` 只保留进程入口和启动逻辑。
- Handler 不包含业务规则和 SQL。
- Service 不依赖 HTTP。
- Repository 不做权限判断。
- 管理接口全部有鉴权和审计。
- 新接口全部有单元测试、路由测试，关键 SQL 有集成测试。
- README 和架构文档保持同步。
