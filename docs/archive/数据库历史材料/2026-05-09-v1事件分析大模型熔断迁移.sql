-- 信息达人 v1.0.0 事件分析大模型熔断增量迁移
-- 适用场景：线上数据库已经执行过 mysql_schema_pro.sql，需要在不重建库的情况下补齐大模型熔断能力。
-- 约束原则：不使用数据库外键，关联一致性由应用代码维护。

ALTER TABLE `llm_model_config`
  ADD COLUMN IF NOT EXISTS `consecutive_failure_count` INT NOT NULL DEFAULT 0 COMMENT '连续失败次数，用于自动熔断' AFTER `priority`,
  ADD COLUMN IF NOT EXISTS `circuit_open_until` DATETIME NULL COMMENT '熔断结束时间，未到期前跳过该模型' AFTER `consecutive_failure_count`,
  ADD COLUMN IF NOT EXISTS `last_failure_reason` VARCHAR(500) NOT NULL DEFAULT '' COMMENT '最近失败原因' AFTER `circuit_open_until`;

SET @idx_exists := (
  SELECT COUNT(1)
  FROM information_schema.statistics
  WHERE table_schema = DATABASE()
    AND table_name = 'llm_model_config'
    AND index_name = 'idx_llm_circuit_open_until'
);
SET @idx_sql := IF(
  @idx_exists = 0,
  'CREATE INDEX `idx_llm_circuit_open_until` ON `llm_model_config` (`circuit_open_until`)',
  'SELECT 1'
);
PREPARE idx_stmt FROM @idx_sql;
EXECUTE idx_stmt;
DEALLOCATE PREPARE idx_stmt;

CREATE TABLE IF NOT EXISTS `llm_call_log` (
  `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '大模型调用日志ID',
  `config_id` BIGINT UNSIGNED NOT NULL COMMENT '大模型配置ID，由代码约束关联llm_model_config.id',
  `provider_code` VARCHAR(50) NOT NULL COMMENT '供应商编码',
  `model_name` VARCHAR(100) NOT NULL COMMENT '模型名称',
  `status` VARCHAR(20) NOT NULL COMMENT '调用状态：succeeded/failed',
  `latency_ms` INT NOT NULL DEFAULT 0 COMMENT '调用耗时毫秒',
  `input_item_count` INT NOT NULL DEFAULT 0 COMMENT '输入来源数量',
  `request_payload` JSON NULL COMMENT '请求参数快照，包含消息内容',
  `response_content` LONGTEXT NULL COMMENT '模型返回文本',
  `response_payload` JSON NULL COMMENT '模型原始响应快照',
  `error_message` VARCHAR(500) NOT NULL DEFAULT '' COMMENT '错误信息',
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  PRIMARY KEY (`id`),
  KEY `idx_llm_call_config_time` (`config_id`, `created_at`),
  KEY `idx_llm_call_status_time` (`status`, `created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='大模型调用日志表：记录事件分析模型调用的成功、失败和耗时';
