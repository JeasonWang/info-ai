-- 信息达人 Max 版本：渠道采集间隔管理化迁移
-- 适用场景：已有 Pro/MySQL 数据库升级到 Max 第一批采集底座能力。

ALTER TABLE `channel`
  ADD COLUMN `base_interval_minutes` INT NOT NULL DEFAULT 60 COMMENT '基础采集间隔，单位分钟，由管理后台配置' AFTER `crawl_interval`,
  ADD COLUMN `hot_interval_minutes` INT NOT NULL DEFAULT 10 COMMENT '热点加速采集间隔，单位分钟' AFTER `base_interval_minutes`,
  ADD COLUMN `min_interval_minutes` INT NOT NULL DEFAULT 3 COMMENT '允许的最小采集间隔，单位分钟' AFTER `hot_interval_minutes`,
  ADD COLUMN `max_interval_minutes` INT NOT NULL DEFAULT 240 COMMENT '失败退避后的最大采集间隔，单位分钟' AFTER `min_interval_minutes`,
  ADD COLUMN `manual_interval_enabled` TINYINT NOT NULL DEFAULT 1 COMMENT '是否启用人工配置间隔：1启用，0禁用' AFTER `max_interval_minutes`,
  ADD COLUMN `effective_interval_minutes` INT NOT NULL DEFAULT 60 COMMENT '当前实际生效采集间隔，单位分钟' AFTER `manual_interval_enabled`,
  ADD COLUMN `schedule_version` INT NOT NULL DEFAULT 1 COMMENT '调度配置版本，用于调度器热更新' AFTER `effective_interval_minutes`;

UPDATE `channel`
SET
  `base_interval_minutes` = `crawl_interval`,
  `hot_interval_minutes` = CASE WHEN `crawl_interval` <= 10 THEN `crawl_interval` ELSE 10 END,
  `min_interval_minutes` = CASE WHEN `crawl_interval` <= 30 THEN 3 ELSE 10 END,
  `max_interval_minutes` = CASE WHEN `crawl_interval` * 4 >= 120 THEN `crawl_interval` * 4 ELSE 120 END,
  `manual_interval_enabled` = 1,
  `effective_interval_minutes` = `crawl_interval`,
  `schedule_version` = 1;
