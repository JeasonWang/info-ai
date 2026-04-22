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

## Pro 后续演进

- 接入 `user_account` 和 `user_session` 表，完成注册入库、登录、退出和会话续期。
- 将管理后台接口迁移到 `info-serve`，管理接口强制登录并写入 `admin_audit_log`。
- 将 `info-max` 用户侧 API 从旧 FastAPI 逐步切换到 `info-serve`。
- 新建 `info-admin` PC Web，展示采集任务、运行日志、健康快照和质量快照。
