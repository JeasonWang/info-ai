-- Max 版本：采集任务调度版本热更新迁移
-- 目的：记录 crawl_task 已同步的 channel.schedule_version，
--      管理后台修改采集间隔后，调度器可刷新 schedule_value 和 next_run_at。

ALTER TABLE `crawl_task`
  ADD COLUMN `schedule_version` INT NOT NULL DEFAULT 0 COMMENT '已同步的调度配置版本' AFTER `schedule_value`;
