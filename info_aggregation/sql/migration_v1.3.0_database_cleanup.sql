-- Migration: v1.3.0 - Database Cleanup
-- Description: 清理废弃表、合并冗余表，减少维护负担
-- Compatible with MySQL 5.7+

-- ========================================
-- Phase 4.1: 确认废弃表无代码引用后删除
-- ========================================

-- crawl_health_snapshot 已被 crawl_run_log 实时统计替代。
DROP TABLE IF EXISTS crawl_health_snapshot;

-- user_follow_keyword 功能未落地，当前 Go/Python 均无读写引用。
DROP TABLE IF EXISTS user_follow_keyword;

-- ========================================
-- Phase 4.2: event_timeline_entry 扩展
-- ========================================

SET @exist := (SELECT COUNT(*) FROM information_schema.COLUMNS
               WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'event_timeline_entry' AND COLUMN_NAME = 'run_id');
SET @sqlstmt := IF(@exist = 0, 'ALTER TABLE event_timeline_entry ADD COLUMN run_id BIGINT UNSIGNED DEFAULT NULL COMMENT ''关联分析运行ID''', 'SELECT 1');
PREPARE stmt FROM @sqlstmt;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @exist := (SELECT COUNT(*) FROM information_schema.COLUMNS
               WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'event_timeline_entry' AND COLUMN_NAME = 'evidence');
SET @sqlstmt := IF(@exist = 0, 'ALTER TABLE event_timeline_entry ADD COLUMN evidence JSON DEFAULT NULL COMMENT ''证据JSON''', 'SELECT 1');
PREPARE stmt FROM @sqlstmt;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;
