-- 信息达人 Max 版本：详情补偿队列迁移
-- 适用场景：已有 Pro/MySQL 数据库升级到详情低分自动补偿能力。

CREATE TABLE IF NOT EXISTS `detail_job` (
  `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '详情补偿任务ID',
  `info_id` BIGINT UNSIGNED NOT NULL COMMENT '信息ID',
  `channel_code` VARCHAR(50) NOT NULL DEFAULT '' COMMENT '渠道编码',
  `status` VARCHAR(20) NOT NULL DEFAULT 'pending' COMMENT '任务状态：pending/running/succeeded/failed/cancelled',
  `priority` INT NOT NULL DEFAULT 50 COMMENT '任务优先级，数值越大越优先',
  `attempt_count` INT NOT NULL DEFAULT 0 COMMENT '已尝试次数',
  `max_attempts` INT NOT NULL DEFAULT 3 COMMENT '最大尝试次数',
  `next_run_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '下次可执行时间',
  `last_failure_reason` VARCHAR(255) NOT NULL DEFAULT '' COMMENT '最近失败原因',
  `strategy_hint` VARCHAR(100) NOT NULL DEFAULT '' COMMENT '建议使用的详情策略',
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_detail_job_info_status` (`info_id`, `status`),
  KEY `idx_detail_job_status_priority` (`status`, `priority`, `next_run_at`),
  KEY `idx_detail_job_channel_status` (`channel_code`, `status`),
  CONSTRAINT `fk_detail_job_info` FOREIGN KEY (`info_id`) REFERENCES `info` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='详情补偿任务表：保存低分、失败或列表态内容的二次抓取任务';
