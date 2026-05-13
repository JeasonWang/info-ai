ALTER TABLE `event`
  ADD COLUMN `display_quality_score` INT NOT NULL DEFAULT 0 COMMENT '展示质量分' AFTER `status`,
  ADD COLUMN `display_quality_level` VARCHAR(20) NOT NULL DEFAULT '' COMMENT '展示质量等级: excellent/good/weak/blocked' AFTER `display_quality_score`,
  ADD COLUMN `display_quality_reason` VARCHAR(500) NOT NULL DEFAULT '' COMMENT '展示质量原因，逗号分隔' AFTER `display_quality_level`;
