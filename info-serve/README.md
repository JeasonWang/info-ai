# info-serve

`info-serve` 是信息达人 Pro 版本的 Go 业务 API 服务，负责用户端 API、管理后台 API、用户鉴权、权限控制、管理审计和业务查询。

## 服务边界

- `info_aggregation` 负责采集、清洗、详情补全、事件构建和写入 MySQL。
- `info-serve` 负责读取 MySQL 并提供业务 API。
- `info-max` 负责用户端展示。
- `info-admin` 负责管理后台展示。

`info-serve` 不负责爬虫采集，不直接渲染页面，不把管理后台页面逻辑混入服务端。

## 当前目录

```text
cmd/
  server/          # HTTP 服务入口，只负责加载配置、创建 app、启动 server
  create-admin/    # 本地管理员账号初始化工具
internal/
  app/             # 服务装配、依赖注入、MySQL handler 构建
  admin/           # 管理后台业务服务
  audit/           # 管理操作审计服务
  auth/            # 用户鉴权和会话服务
  config/          # 环境变量配置
  events/          # 用户侧事件查询服务
  handler/         # 历史 HTTP handler，当前仍保留管理 handler
  middleware/      # 鉴权和审计中间件
  repository/      # MySQL 数据访问
  response/        # 统一 JSON 响应
  router/          # 历史兼容路由包装
  transport/http/  # 新 HTTP 路由装配入口
```

后续新增 HTTP 代码必须优先进入 `internal/transport/http`。`health`、`auth` 和 `events` handler 已迁入该目录；现有 `handler` 中仍保留管理后台 handler，后续继续小步迁移。迁移时必须保持 API 行为不变并补充路由测试。

## 本地启动

```bash
cd /Users/jeasonwang/IdeaProjects/info-ai/info-serve
INFO_SERVE_HTTP_ADDR=:8080 go run ./cmd/server
```

默认 MySQL DSN：

```text
root:root1234@tcp(localhost:3306)/info-max?charset=utf8mb4&parseTime=true&loc=Local
```

可通过环境变量覆盖：

```text
INFO_SERVE_MYSQL_DSN
INFO_SERVE_HTTP_ADDR
INFO_SERVE_SESSION_SECRET
```

## 本地测试

```bash
cd /Users/jeasonwang/IdeaProjects/info-ai/info-serve
GOCACHE=/tmp/info-serve-go-build-cache go test ./...
```

真实 MySQL 集成测试：

```bash
cd /Users/jeasonwang/IdeaProjects/info-ai/info-serve
GOCACHE=/tmp/info-serve-go-build-cache \
INFO_SERVE_TEST_MYSQL_DSN='root:root1234@tcp(127.0.0.1:3306)/info-max?charset=utf8mb4&parseTime=true&loc=Local' \
go test ./internal/repository -v
```

## 初始化管理员账号

```bash
cd /Users/jeasonwang/IdeaProjects/info-ai/info-serve
INFO_SERVE_MYSQL_DSN='root:root1234@tcp(localhost:3306)/info-max?charset=utf8mb4&parseTime=true&loc=Local' \
go run ./cmd/create-admin -email admin@example.com -password StrongerPass123
```

## 架构规则

- `cmd/server/main.go` 只保留进程入口和启动逻辑。
- `handler` 只解析 HTTP 请求和响应，不写 SQL，不写复杂业务规则。
- `internal/router` 只保留兼容入口，新路由统一放入 `internal/transport/http`。
- `service` 处理业务规则、参数归一化、权限语义。
- `repository` 只负责 SQL、事务和数据映射。
- `response` 统一输出 `{ code, message, data }`。
- 管理接口必须经过管理员鉴权，并写入审计日志。
- 新增接口必须先写测试，再写实现。
- 数据库结构变更必须保存 SQL 文件，字段必须带中文注释。
