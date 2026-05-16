-- Phase 1: Cookie 数据库化 - 数据库迁移脚本
-- 执行时间: 2026-05-11
-- 版本: v1.1.0

-- ============================================
-- 1. channel 表字段变更
-- ============================================

-- 新增凭证相关字段。使用 information_schema 判断，保证脚本可重复执行。
SET @exist := (SELECT COUNT(*) FROM information_schema.COLUMNS
               WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'channel' AND COLUMN_NAME = 'cookies');
SET @sqlstmt := IF(@exist = 0, 'ALTER TABLE channel ADD COLUMN cookies TEXT DEFAULT NULL COMMENT ''采集Cookie凭证(JSON格式)'' AFTER is_active', 'SELECT 1');
PREPARE stmt FROM @sqlstmt;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @exist := (SELECT COUNT(*) FROM information_schema.COLUMNS
               WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'channel' AND COLUMN_NAME = 'extra_credentials');
SET @sqlstmt := IF(@exist = 0, 'ALTER TABLE channel ADD COLUMN extra_credentials JSON DEFAULT NULL COMMENT ''扩展凭证(如知乎zse_93/zse_96)'' AFTER cookies', 'SELECT 1');
PREPARE stmt FROM @sqlstmt;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @exist := (SELECT COUNT(*) FROM information_schema.COLUMNS
               WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'channel' AND COLUMN_NAME = 'credentials_updated_at');
SET @sqlstmt := IF(@exist = 0, 'ALTER TABLE channel ADD COLUMN credentials_updated_at DATETIME DEFAULT NULL COMMENT ''凭证最后更新时间'' AFTER extra_credentials', 'SELECT 1');
PREPARE stmt FROM @sqlstmt;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @exist := (SELECT COUNT(*) FROM information_schema.COLUMNS
               WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'channel' AND COLUMN_NAME = 'credentials_updated_by');
SET @sqlstmt := IF(@exist = 0, 'ALTER TABLE channel ADD COLUMN credentials_updated_by VARCHAR(100) DEFAULT '''' COMMENT ''最后更新人'' AFTER credentials_updated_at', 'SELECT 1');
PREPARE stmt FROM @sqlstmt;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- 删除冗余字段 crawl_interval（已被 base_interval_minutes/effective_interval_minutes 取代）。
-- 当前库可能已经删除该字段，因此迁移前先判断，避免重复执行失败。
SET @has_crawl_interval := (SELECT COUNT(*) FROM information_schema.COLUMNS
                            WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'channel' AND COLUMN_NAME = 'crawl_interval');
SET @sqlstmt := IF(@has_crawl_interval = 1,
  'UPDATE channel SET base_interval_minutes = crawl_interval WHERE (base_interval_minutes = 0 OR base_interval_minutes IS NULL) AND crawl_interval IS NOT NULL',
  'SELECT 1');
PREPARE stmt FROM @sqlstmt;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @sqlstmt := IF(@has_crawl_interval = 1, 'ALTER TABLE channel DROP COLUMN crawl_interval', 'SELECT 1');
PREPARE stmt FROM @sqlstmt;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- ============================================
-- 2. 创建索引（可选，用于凭证查询优化）
-- ============================================
-- 如果经常按 code 查询凭证，可以添加索引（channel.code 已唯一，不需要额外索引）

-- ============================================
-- 3. 验证脚本
-- ============================================

-- 验证字段是否添加成功
DESCRIBE channel;

-- 验证现有渠道数据是否完整
SELECT id, name, code, cookies, extra_credentials, credentials_updated_at, credentials_updated_by
FROM channel
LIMIT 10;

-- ============================================
-- 回滚脚本（如需要回滚）
-- ============================================
/*
-- 添加回退字段
ALTER TABLE channel
  ADD COLUMN crawl_interval INT DEFAULT 60 COMMENT '爬取间隔(分钟)' AFTER is_active;

-- 恢复数据
UPDATE channel SET crawl_interval = base_interval_minutes WHERE base_interval_minutes > 0;

-- 删除新增字段
ALTER TABLE channel
  DROP COLUMN cookies,
  DROP COLUMN extra_credentials,
  DROP COLUMN credentials_updated_at,
  DROP COLUMN credentials_updated_by;
*/
