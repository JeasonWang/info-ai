-- Migration: v1.2.0 - Event Historical Context Analysis
-- Description: 事件历史脉络分析，支持事件演变追踪和完整时间线构建
-- Compatible with MySQL 5.7+

-- 修改 event 表，添加历史脉络相关字段
SET @exist := (SELECT COUNT(*) FROM information_schema.COLUMNS
               WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'event' AND COLUMN_NAME = 'previous_event_id');
SET @sqlstmt := IF(@exist = 0, 'ALTER TABLE event ADD COLUMN previous_event_id BIGINT UNSIGNED DEFAULT NULL COMMENT ''同实体前序事件ID''', 'SELECT 1');
PREPARE stmt FROM @sqlstmt;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @exist := (SELECT COUNT(*) FROM information_schema.COLUMNS
               WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'event' AND COLUMN_NAME = 'event_generation');
SET @sqlstmt := IF(@exist = 0, 'ALTER TABLE event ADD COLUMN event_generation INT UNSIGNED DEFAULT 1 COMMENT ''事件代数''', 'SELECT 1');
PREPARE stmt FROM @sqlstmt;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @exist := (SELECT COUNT(*) FROM information_schema.COLUMNS
               WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'event' AND COLUMN_NAME = 'evolution_stage');
SET @sqlstmt := IF(@exist = 0, 'ALTER TABLE event ADD COLUMN evolution_stage VARCHAR(20) DEFAULT ''emerging'' COMMENT ''演变阶段: emerging/peak/declining/resolved/recurring''', 'SELECT 1');
PREPARE stmt FROM @sqlstmt;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- 添加索引
SET @exist := (SELECT COUNT(*) FROM information_schema.STATISTICS
               WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'event' AND INDEX_NAME = 'idx_event_core_entity');
SET @sqlstmt := IF(@exist = 0, 'ALTER TABLE event ADD INDEX idx_event_core_entity (event_key, event_generation)', 'SELECT 1');
PREPARE stmt FROM @sqlstmt;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- 新增 event_evolution 表（TEXT 字段不使用 DEFAULT）
CREATE TABLE IF NOT EXISTS event_evolution (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    event_id BIGINT UNSIGNED NOT NULL COMMENT '当前事件ID',
    previous_event_id BIGINT UNSIGNED DEFAULT NULL COMMENT '前序事件ID',
    evolution_type VARCHAR(30) DEFAULT '' COMMENT '演变类型: escalation/expansion/correction/recurrence/none',
    evolution_summary TEXT COMMENT '演变摘要: 本事件相比前序事件的增量变化',
    source_count_delta INT DEFAULT 0 COMMENT '来源数变化(正=增加)',
    key_change TEXT COMMENT '关键变化描述',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,

    INDEX idx_event_evolution_event_id (event_id),
    INDEX idx_event_evolution_previous_event_id (previous_event_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='事件演变记录表';
