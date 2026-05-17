-- ============================================================
-- v3: daily_brief table
-- ============================================================

USE `info-max`;

CREATE TABLE IF NOT EXISTS `daily_brief` (
  `id` BIGINT NOT NULL AUTO_INCREMENT,
  `brief_date` DATE NOT NULL COMMENT '简报日期',
  `headline` VARCHAR(200) NOT NULL DEFAULT '' COMMENT '简报标题',
  `content_md` TEXT COMMENT 'Markdown格式内容',
  `content_html` TEXT COMMENT 'HTML格式内容(公众号用)',
  `content_text` TEXT COMMENT '纯文本内容',
  `event_ids` JSON COMMENT '包含的事件ID列表',
  `event_count` INT NOT NULL DEFAULT 0,
  `status` VARCHAR(20) NOT NULL DEFAULT 'draft' COMMENT 'draft/published/archived',
  `model_name` VARCHAR(100) NOT NULL DEFAULT '' COMMENT '生成用的模型',
  `llm_config_id` INT DEFAULT NULL COMMENT 'LLM配置ID',
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_brief_date` (`brief_date`),
  KEY `idx_daily_brief_status` (`status`, `brief_date`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='每日情报简报';

-- verify
SELECT 'daily_brief' AS tbl, COUNT(*) AS cnt FROM `daily_brief`;