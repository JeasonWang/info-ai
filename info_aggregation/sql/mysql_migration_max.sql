-- 信息达人 Max 版本 MySQL 初始化数据脚本
-- 目标数据库：MySQL 8.x
-- 职责边界：
-- 1. 本文件只负责初始化必要数据，不负责创建表结构，不负责 ALTER 表结构。
-- 2. 表结构请先执行 mysql_schema_pro.sql。
-- 3. 本文件可重复执行，初始化数据使用幂等写法。
-- 4. 默认管理员账号：
--      邮箱：admin@info-daren.local
--      默认密码：Admin123456
--    仅供本地/首次部署初始化使用，生产环境首次登录后必须立即修改密码或使用 create-admin 工具覆盖。

USE `info-max`;

-- ------------------------------------------------------------
-- 基础分类初始化
-- ------------------------------------------------------------

INSERT INTO `category` (`name`, `code`, `description`)
VALUES
  ('热点事件', 'hot', '微博、头条、小红书、知乎等平台的热点事件'),
  ('经济数据', 'economy', '金价、油价、汇率、宏观数据等经济指标'),
  ('国际大事', 'international', '国际政治、地缘冲突、外交与全球公共事件'),
  ('科技动向', 'tech', '软件工程、云原生、开发者生态、硬件与互联网科技'),
  ('AI大模型', 'ai', 'AI模型、智能体、多模态、AI产品与产业动态'),
  ('体育赛事', 'sports', '足球、篮球、综合体育赛事与体育新闻')
ON DUPLICATE KEY UPDATE
  `name` = VALUES(`name`),
  `description` = VALUES(`description`),
  `updated_at` = CURRENT_TIMESTAMP;

-- ------------------------------------------------------------
-- Max 当前采集渠道初始化
-- ------------------------------------------------------------

INSERT INTO `channel` (
  `name`, `code`, `base_url`, `category_id`, `crawl_interval`,
  `base_interval_minutes`, `hot_interval_minutes`, `min_interval_minutes`,
  `max_interval_minutes`, `manual_interval_enabled`, `effective_interval_minutes`,
  `schedule_version`, `is_active`
)
VALUES
  ('微博', 'weibo', 'https://weibo.com', (SELECT `id` FROM `category` WHERE `code` = 'hot'), 30, 30, 10, 3, 120, 1, 30, 1, 1),
  ('今日头条', 'toutiao', 'https://www.toutiao.com', (SELECT `id` FROM `category` WHERE `code` = 'hot'), 30, 30, 10, 3, 120, 1, 30, 1, 1),
  ('小红书', 'xiaohongshu', 'https://www.xiaohongshu.com', (SELECT `id` FROM `category` WHERE `code` = 'hot'), 30, 30, 10, 3, 120, 1, 30, 1, 1),
  ('知乎', 'zhihu', 'https://www.zhihu.com', (SELECT `id` FROM `category` WHERE `code` = 'ai'), 60, 60, 10, 10, 240, 1, 60, 1, 1),
  ('东方财富网', 'eastmoney', 'https://www.eastmoney.com', (SELECT `id` FROM `category` WHERE `code` = 'economy'), 60, 60, 10, 10, 240, 1, 60, 1, 1),
  ('路透社', 'reuters', 'https://www.reuters.com', (SELECT `id` FROM `category` WHERE `code` = 'international'), 120, 120, 10, 10, 480, 1, 120, 1, 1),
  ('CSDN', 'csdn', 'https://blog.csdn.net', (SELECT `id` FROM `category` WHERE `code` = 'tech'), 120, 120, 10, 10, 480, 1, 120, 1, 1),
  ('掘金', 'juejin', 'https://juejin.cn', (SELECT `id` FROM `category` WHERE `code` = 'tech'), 120, 120, 10, 10, 480, 1, 120, 1, 1),
  ('博客园', 'cnblogs', 'https://www.cnblogs.com', (SELECT `id` FROM `category` WHERE `code` = 'tech'), 120, 120, 10, 10, 480, 1, 120, 1, 1),
  ('36氪', '36kr', 'https://36kr.com', (SELECT `id` FROM `category` WHERE `code` = 'ai'), 120, 120, 10, 10, 480, 1, 120, 1, 1),
  ('央视体育网', 'cctv_sports', 'https://sports.cctv.com', (SELECT `id` FROM `category` WHERE `code` = 'sports'), 60, 60, 10, 10, 240, 1, 60, 1, 1),
  ('新浪体育', 'sina_sports', 'https://sports.sina.com.cn', (SELECT `id` FROM `category` WHERE `code` = 'sports'), 60, 60, 10, 10, 240, 1, 60, 1, 1)
ON DUPLICATE KEY UPDATE
  `name` = VALUES(`name`),
  `base_url` = VALUES(`base_url`),
  `category_id` = VALUES(`category_id`),
  `crawl_interval` = VALUES(`crawl_interval`),
  `base_interval_minutes` = VALUES(`base_interval_minutes`),
  `hot_interval_minutes` = VALUES(`hot_interval_minutes`),
  `min_interval_minutes` = VALUES(`min_interval_minutes`),
  `max_interval_minutes` = VALUES(`max_interval_minutes`),
  `manual_interval_enabled` = VALUES(`manual_interval_enabled`),
  `effective_interval_minutes` = VALUES(`effective_interval_minutes`),
  `schedule_version` = GREATEST(`schedule_version`, VALUES(`schedule_version`)),
  `is_active` = VALUES(`is_active`),
  `updated_at` = CURRENT_TIMESTAMP;

-- ------------------------------------------------------------
-- 采集任务初始化：每个启用渠道一条 interval 任务
-- ------------------------------------------------------------

INSERT INTO `crawl_task` (
  `channel_id`, `task_code`, `task_name`, `schedule_type`,
  `schedule_value`, `schedule_version`, `status`, `next_run_at`
)
SELECT
  ch.`id`,
  CONCAT(ch.`code`, '_interval_crawl'),
  CONCAT(ch.`name`, '定时采集'),
  'interval',
  CAST(ch.`effective_interval_minutes` AS CHAR),
  ch.`schedule_version`,
  CASE WHEN ch.`is_active` = 1 THEN 'active' ELSE 'disabled' END,
  CURRENT_TIMESTAMP
FROM `channel` AS ch
ON DUPLICATE KEY UPDATE
  `channel_id` = VALUES(`channel_id`),
  `task_name` = VALUES(`task_name`),
  `schedule_type` = VALUES(`schedule_type`),
  `schedule_value` = VALUES(`schedule_value`),
  `schedule_version` = VALUES(`schedule_version`),
  `status` = VALUES(`status`),
  `next_run_at` = COALESCE(`next_run_at`, CURRENT_TIMESTAMP),
  `updated_at` = CURRENT_TIMESTAMP;

-- ------------------------------------------------------------
-- 默认管理员初始化
-- 默认密码 Admin123456。生产环境首次登录后必须修改。
-- ------------------------------------------------------------

INSERT INTO `user_account` (`email`, `password_hash`, `display_name`, `role`, `status`, `email_verified_at`)
VALUES (
  'admin@info-daren.local',
  'pbkdf2_sha256$210000$NXiTL/HJ37ndl7tJUadNUQ$HXhBu0gh3QNYIwlAwq/dYEmvJrTcu8aa4oArWZJZS9Y',
  '系统管理员',
  'admin',
  'active',
  CURRENT_TIMESTAMP
)
ON DUPLICATE KEY UPDATE
  `role` = 'admin',
  `status` = 'active',
  `display_name` = IF(`display_name` = '', VALUES(`display_name`), `display_name`),
  `updated_at` = CURRENT_TIMESTAMP;

-- ------------------------------------------------------------
-- 初始治理快照：让管理端空库时有全局质量基线记录
-- ------------------------------------------------------------

INSERT INTO `data_quality_snapshot` (
  `category_code`, `total_count`, `duplicate_title_count`,
  `empty_content_count`, `low_detail_score_count`, `missing_entity_count`,
  `snapshot_payload`, `snapshot_at`
)
SELECT
  'all',
  stats.`total_count`,
  0,
  stats.`empty_content_count`,
  stats.`low_detail_score_count`,
  stats.`missing_entity_count`,
  JSON_OBJECT('source', 'mysql_migration_max', 'created_by', 'migration', 'note', 'initial quality baseline'),
  CURRENT_TIMESTAMP
FROM (
  SELECT
    COUNT(*) AS `total_count`,
    COALESCE(SUM(CASE WHEN COALESCE(`content`, '') = '' THEN 1 ELSE 0 END), 0) AS `empty_content_count`,
    COALESCE(SUM(CASE WHEN `detail_score` < 60 THEN 1 ELSE 0 END), 0) AS `low_detail_score_count`,
    COALESCE(SUM(CASE WHEN COALESCE(`core_entity`, '') = '' THEN 1 ELSE 0 END), 0) AS `missing_entity_count`
  FROM `info`
) AS stats
WHERE NOT EXISTS (
  SELECT 1
  FROM `data_quality_snapshot`
  WHERE `category_code` = 'all'
);

INSERT INTO `crawl_health_snapshot` (
  `channel_code`, `success_rate`, `detail_complete_rate`, `avg_detail_score`,
  `last_success_at`, `last_failed_at`, `snapshot_at`
)
SELECT
  ch.`code`,
  0.00,
  0.00,
  0.00,
  NULL,
  NULL,
  CURRENT_TIMESTAMP
FROM `channel` AS ch
WHERE NOT EXISTS (
  SELECT 1
  FROM `crawl_health_snapshot` AS snap
  WHERE snap.`channel_code` = ch.`code`
);

-- ------------------------------------------------------------
-- 初始化完成检查
-- ------------------------------------------------------------

SELECT 'category' AS `table_name`, COUNT(*) AS `row_count` FROM `category`
UNION ALL
SELECT 'channel', COUNT(*) FROM `channel`
UNION ALL
SELECT 'crawl_task', COUNT(*) FROM `crawl_task`
UNION ALL
SELECT 'user_account', COUNT(*) FROM `user_account`;
