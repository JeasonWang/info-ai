-- ============================================================
-- v2: Ollama + system_config + channel credibility_tier
-- ============================================================

USE `info-max`;

-- 1. system_config table
CREATE TABLE IF NOT EXISTS `system_config` (
  `id` INT UNSIGNED NOT NULL AUTO_INCREMENT,
  `config_key` VARCHAR(80) NOT NULL COMMENT 'config key',
  `config_value` TEXT NOT NULL COMMENT 'config value',
  `value_type` VARCHAR(20) NOT NULL DEFAULT 'string' COMMENT 'string/int/float/bool/json',
  `description` VARCHAR(200) NOT NULL DEFAULT '' COMMENT 'description',
  `updated_by` VARCHAR(50) NOT NULL DEFAULT '' COMMENT 'last updater',
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_config_key` (`config_key`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 2. initial config values
INSERT INTO `system_config` (`config_key`, `config_value`, `value_type`, `description`) VALUES
  ('event_analysis_mode',       'hybrid',  'string', 'event analysis mode: rule / hybrid / llm'),
  ('event_analysis_enable_llm', '1',       'bool',   'enable LLM enhancement (0=off, 1=on)'),
  ('event_analysis_temperature','0.2',     'float',  'LLM temperature'),
  ('event_analysis_timeout',    '120',     'int',    'LLM call timeout seconds'),
  ('event_analysis_max_input_chars', '12000', 'int', 'LLM max input chars'),
  ('daily_brief_enabled',      '1',       'bool',   'enable daily brief generation'),
  ('daily_brief_hour',         '7',       'int',    'daily brief hour (24h)'),
  ('daily_brief_minute',       '30',      'int',    'daily brief minute'),
  ('daily_brief_top_n',        '5',       'int',    'daily brief top N events'),
  ('event_analysis_fallback_to_rule', '1', 'bool', 'fallback to rule when LLM fails'),
  ('event_analysis_llm_retry_times',  '2', 'int',  'LLM retry times on failure')
ON DUPLICATE KEY UPDATE `description` = VALUES(`description`);

-- 3. Ollama model config
INSERT INTO `llm_model_config` (
  `provider_name`, `provider_code`, `base_url`, `api_key`, `model_name`,
  `is_enabled`, `daily_call_limit`, `daily_call_count`, `last_call_date`, `priority`,
  `consecutive_failure_count`, `circuit_open_until`, `last_failure_reason`
) VALUES (
  'Ollama', 'ollama', 'http://localhost:11434/v1', '', 'qwen2.5:7b',
  1, 2000, 0, CURRENT_DATE, 5,
  0, NULL, ''
)
ON DUPLICATE KEY UPDATE
  `base_url` = VALUES(`base_url`),
  `is_enabled` = VALUES(`is_enabled`),
  `priority` = VALUES(`priority`),
  `daily_call_limit` = VALUES(`daily_call_limit`),
  `updated_at` = CURRENT_TIMESTAMP;

-- 4. channel credibility_tier
-- Add credibility_tier if not exists (MySQL 8.0 safe)
SET @col_exists = (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'channel' AND COLUMN_NAME = 'credibility_tier');
SET @sql = IF(@col_exists = 0, 'ALTER TABLE `channel` ADD COLUMN `credibility_tier` TINYINT NOT NULL DEFAULT 2 COMMENT ''1=official/authority, 2=professional media/tech, 3=social/UGC'' AFTER `is_active`', 'SELECT ''credibility_tier already exists''');
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

UPDATE `channel` SET `credibility_tier` = 1 WHERE `code` IN ('reuters', 'cctv_sports', 'sina_sports');
UPDATE `channel` SET `credibility_tier` = 2 WHERE `code` IN ('eastmoney', '36kr', 'csdn', 'juejin', 'cnblogs', 'zhihu', 'toutiao');
UPDATE `channel` SET `credibility_tier` = 3 WHERE `code` IN ('weibo', 'xiaohongshu');

-- 5. verify
SELECT 'system_config' AS tbl, COUNT(*) AS cnt FROM `system_config`
UNION ALL SELECT 'ollama', COUNT(*) FROM `llm_model_config` WHERE `provider_code` = 'ollama'
UNION ALL SELECT 'channels', COUNT(*) FROM `channel` WHERE `credibility_tier` IS NOT NULL;