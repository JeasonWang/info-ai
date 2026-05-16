-- Migration: v1.4.0 - Incremental Event Building
-- Description: 支持增量事件构建，提高rebuild性能

-- 新增 rebuild_checkpoint 表：记录增量/全量重建的进度和状态
CREATE TABLE IF NOT EXISTS rebuild_checkpoint (
    id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    checkpoint_type VARCHAR(30) DEFAULT 'incremental' COMMENT 'incremental / full',
    max_info_id_processed INT DEFAULT 0 COMMENT '已处理的最大InfoID',
    max_event_time_processed DATETIME DEFAULT NULL COMMENT '已处理的最大事件时间',
    events_created INT DEFAULT 0 COMMENT '本次新建事件数',
    events_updated INT DEFAULT 0 COMMENT '本次更新事件数',
    items_processed INT DEFAULT 0 COMMENT '本次处理Info数',
    started_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    finished_at DATETIME DEFAULT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,

    INDEX idx_rebuild_checkpoint_type (checkpoint_type, created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='事件重建检查点表';
