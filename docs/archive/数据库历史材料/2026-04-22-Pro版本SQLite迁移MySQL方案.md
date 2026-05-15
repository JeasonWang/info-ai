# Pro版本SQLite迁移MySQL方案

## 迁移目标

把 Plus 阶段 SQLite 中已经采集和治理过的数据迁移到 Pro 版本 MySQL，保留分类、渠道、原始内容、详情采集日志、事件、时间线和摘要数据。

## 不迁移的数据

- `user_account`、`user_session`、`admin_audit_log` 等 Pro 新增表没有历史数据，不从 SQLite 迁移。
- 本地前端缓存的筛选条件仍用于匿名用户；登录用户首页筛选偏好已同步到 `user_preference`。

## 迁移命令

```bash
cd /Users/jeasonwang/IdeaProjects/info-ai/info_aggregation
./.venv/bin/python sql/mysql_migration_from_sqlite.py \
  --sqlite-path info_aggregation.db \
  --mysql-host localhost \
  --mysql-port 3306 \
  --mysql-user root \
  --mysql-password root1234 \
  --mysql-db info-max
```

## 校验方式

- 迁移脚本会先执行 `mysql_schema_pro.sql`，确保 MySQL 表结构存在。
- 数据按外键依赖顺序迁移：分类、渠道、内容、事件、关联、时间线、摘要。
- 迁移完成后，应对比 SQLite 与 MySQL 的核心表数量，并抽查事件详情页所需字段。
