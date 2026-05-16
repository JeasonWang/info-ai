-- Migration: v1.1.0 - Event Analysis Source Tracking
-- Description: 记录事件分析过程中使用的来源信息，实现溯源能力
-- Compatible with MySQL 5.7+

-- 事件分析来源表：记录每次分析运行使用的Info来源
CREATE TABLE IF NOT EXISTS event_analysis_source (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    run_id BIGINT UNSIGNED NOT NULL COMMENT '关联的分析运行ID',
    info_id BIGINT UNSIGNED NOT NULL COMMENT 'Info记录ID',
    info_title VARCHAR(200) DEFAULT '' COMMENT 'Info标题快照',
    role VARCHAR(20) DEFAULT 'media' COMMENT '角色: primary/background/media',
    weight INT DEFAULT 0 COMMENT '权重分',
    quality_score INT DEFAULT 0 COMMENT '质量分',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,

    INDEX idx_run_id (run_id),
    INDEX idx_info_id (info_id),
    UNIQUE KEY uq_event_analysis_source_run_info (run_id, info_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='事件分析来源记录表';

-- 修改 event_analysis_run 表，添加 event_id 字段
SET @exist := (SELECT COUNT(*) FROM information_schema.COLUMNS
               WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'event_analysis_run' AND COLUMN_NAME = 'event_id');
SET @sqlstmt := IF(@exist = 0, 'ALTER TABLE event_analysis_run ADD COLUMN event_id BIGINT UNSIGNED COMMENT ''关联的事件ID''', 'SELECT 1');
PREPARE stmt FROM @sqlstmt;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- 添加索引
SET @exist := (SELECT COUNT(*) FROM information_schema.STATISTICS
               WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'event_analysis_run' AND INDEX_NAME = 'idx_event_id');
SET @sqlstmt := IF(@exist = 0, 'ALTER TABLE event_analysis_run ADD INDEX idx_event_id (event_id)', 'SELECT 1');
PREPARE stmt FROM @sqlstmt;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;
