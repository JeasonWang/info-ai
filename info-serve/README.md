# info-serve

`info-serve` 是信息达人 Pro 版本新增的 Go 服务，负责业务 API、用户鉴权、管理侧接口和对外服务边界。

## 当前职责

- 用户服务：提供健康检查、邮箱注册接口契约。
- 鉴权基础：提供密码哈希与校验能力。
- 服务配置：通过环境变量读取监听地址、MySQL DSN、会话密钥。

## 本地启动

```bash
cd /Users/jeasonwang/IdeaProjects/info-ai/info-serve
INFO_SERVE_HTTP_ADDR=:8080 go run ./cmd/server
```

## 本地测试

```bash
cd /Users/jeasonwang/IdeaProjects/info-ai/info-serve
GOCACHE=/tmp/info-serve-go-build-cache go test ./...
```

## 初始化管理员账号

管理后台不开放普通注册成为管理员。Pro 初期可以使用命令行工具初始化或重置首个管理员账号：

```bash
cd /Users/jeasonwang/IdeaProjects/info-ai/info-serve
INFO_SERVE_MYSQL_DSN='root:root1234@tcp(localhost:3306)/info-max?charset=utf8mb4&parseTime=true&loc=Local' \
go run ./cmd/create-admin -email admin@example.com -password StrongerPass123
```

## Pro 后续演进

- 将管理后台接口迁移到 `info-serve`，管理接口强制登录并写入 `admin_audit_log`。
- 将 `info-max` 用户侧 API 从旧 FastAPI 逐步切换到 `info-serve`。
- 新建 `info-admin` PC Web，展示采集任务、运行日志、健康快照和质量快照。
