-- 信息达人 Max 首版 MySQL 8 一键初始化脚本
-- 生成来源：本地正式数据库 info-max 的表结构 + 首次部署必需基础数据
-- 适用版本：MySQL 8.x
-- 说明：
-- 1. 用于首次部署空库初始化；默认不删除已有库和已有数据。
-- 2. 真实 Cookie / ZSE / API Key 不写入脚本，需通过管理后台配置。
-- 3. 默认管理员账号：admin@info-daren.local；默认密码：Admin123456。生产首次登录后必须修改。

SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

CREATE DATABASE IF NOT EXISTS `info-max`
  DEFAULT CHARACTER SET utf8mb4
  COLLATE utf8mb4_0900_ai_ci;

USE `info-max`;

-- ============================================================
-- 表结构：以本地正式库 info-max 为准
-- ============================================================

CREATE TABLE IF NOT EXISTS `admin_audit_log` (
  `id` bigint unsigned NOT NULL AUTO_INCREMENT COMMENT '管理后台操作审计日志ID',
  `admin_user_id` bigint unsigned NOT NULL COMMENT '管理员用户ID',
  `action` varchar(80) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '操作动作',
  `target_type` varchar(80) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT '' COMMENT '操作对象类型',
  `target_id` varchar(80) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT '' COMMENT '操作对象ID',
  `request_payload` json DEFAULT NULL COMMENT '请求参数快照',
  `ip_address` varchar(64) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT '' COMMENT '操作IP地址',
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  PRIMARY KEY (`id`),
  KEY `idx_admin_audit_user_time` (`admin_user_id`,`created_at`),
  KEY `idx_admin_audit_action_time` (`action`,`created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='管理后台审计表：记录管理员关键操作';

CREATE TABLE IF NOT EXISTS `category` (
  `id` bigint unsigned NOT NULL AUTO_INCREMENT COMMENT '分类ID',
  `name` varchar(50) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '分类名称',
  `code` varchar(50) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '分类编码',
  `description` varchar(200) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT '' COMMENT '分类描述',
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_category_name` (`name`),
  UNIQUE KEY `uk_category_code` (`code`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='分类表：保存热点、科技、体育等内容分类';

CREATE TABLE IF NOT EXISTS `channel` (
  `id` bigint unsigned NOT NULL AUTO_INCREMENT COMMENT '渠道ID',
  `name` varchar(50) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '渠道名称',
  `code` varchar(50) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '渠道编码',
  `base_url` varchar(255) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT '' COMMENT '渠道基础URL',
  `category_id` bigint unsigned NOT NULL COMMENT '关联分类ID',
  `base_interval_minutes` int NOT NULL DEFAULT '60' COMMENT '基础采集间隔，单位分钟，由管理后台配置',
  `hot_interval_minutes` int NOT NULL DEFAULT '10' COMMENT '热点加速采集间隔，单位分钟',
  `min_interval_minutes` int NOT NULL DEFAULT '3' COMMENT '允许的最小采集间隔，单位分钟',
  `max_interval_minutes` int NOT NULL DEFAULT '240' COMMENT '失败退避后的最大采集间隔，单位分钟',
  `manual_interval_enabled` tinyint NOT NULL DEFAULT '1' COMMENT '是否启用人工配置间隔：1启用，0禁用',
  `effective_interval_minutes` int NOT NULL DEFAULT '60' COMMENT '当前实际生效采集间隔，单位分钟',
  `schedule_version` int NOT NULL DEFAULT '1' COMMENT '调度配置版本，用于调度器热更新',
  `is_active` tinyint NOT NULL DEFAULT '1' COMMENT '是否启用：1启用，0停用',
  `cookies` text COLLATE utf8mb4_unicode_ci COMMENT '采集Cookie凭证(JSON格式)',
  `extra_credentials` json DEFAULT NULL COMMENT '扩展凭证(如知乎zse_93/zse_96)',
  `credentials_updated_at` datetime DEFAULT NULL COMMENT '凭证最后更新时间',
  `credentials_updated_by` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT '' COMMENT '最后更新人',
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_channel_name` (`name`),
  UNIQUE KEY `uk_channel_code` (`code`),
  KEY `idx_channel_category` (`category_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='渠道表：保存微博、央视体育网、CSDN等采集来源';

CREATE TABLE IF NOT EXISTS `crawl_run_log` (
  `id` bigint unsigned NOT NULL AUTO_INCREMENT COMMENT '采集运行日志ID',
  `task_id` bigint unsigned DEFAULT NULL COMMENT '采集任务ID',
  `channel_code` varchar(50) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '渠道编码',
  `trigger_type` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'scheduler' COMMENT '触发方式：scheduler/manual/retry',
  `status` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '运行状态：success/partial/failed',
  `raw_count` int NOT NULL DEFAULT '0' COMMENT '原始抓取数量',
  `cleaned_count` int NOT NULL DEFAULT '0' COMMENT '清洗后数量',
  `saved_count` int NOT NULL DEFAULT '0' COMMENT '入库数量',
  `detail_success_count` int NOT NULL DEFAULT '0' COMMENT '详情成功数量',
  `detail_failed_count` int NOT NULL DEFAULT '0' COMMENT '详情失败数量',
  `error_message` varchar(1000) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT '' COMMENT '错误信息',
  `started_at` datetime NOT NULL COMMENT '开始时间',
  `finished_at` datetime DEFAULT NULL COMMENT '结束时间',
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  PRIMARY KEY (`id`),
  KEY `idx_crawl_run_channel_time` (`channel_code`,`started_at`),
  KEY `idx_crawl_run_task_time` (`task_id`,`started_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='采集运行日志表：记录每次采集执行结果';

CREATE TABLE IF NOT EXISTS `crawl_task` (
  `id` bigint unsigned NOT NULL AUTO_INCREMENT COMMENT '采集任务ID',
  `channel_id` bigint unsigned NOT NULL COMMENT '渠道ID',
  `task_code` varchar(80) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '任务编码',
  `task_name` varchar(100) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '任务名称',
  `schedule_type` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'interval' COMMENT '调度类型：interval/manual/cron',
  `schedule_value` varchar(100) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT '' COMMENT '调度配置值',
  `schedule_version` int NOT NULL DEFAULT '0' COMMENT '已同步的调度配置版本',
  `status` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'active' COMMENT '任务状态：active/paused/disabled',
  `last_run_at` datetime DEFAULT NULL COMMENT '最近运行时间',
  `next_run_at` datetime DEFAULT NULL COMMENT '下次计划运行时间',
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_crawl_task_code` (`task_code`),
  KEY `idx_crawl_task_channel_status` (`channel_id`,`status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='采集任务表：保存可调度的数据采集任务';

CREATE TABLE IF NOT EXISTS `data_quality_snapshot` (
  `id` bigint unsigned NOT NULL AUTO_INCREMENT COMMENT '质量快照ID',
  `category_code` varchar(50) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'all' COMMENT '分类编码，all表示全局',
  `total_count` int NOT NULL DEFAULT '0' COMMENT '总内容数量',
  `duplicate_title_count` int NOT NULL DEFAULT '0' COMMENT '重复标题数量',
  `empty_content_count` int NOT NULL DEFAULT '0' COMMENT '正文为空数量',
  `low_detail_score_count` int NOT NULL DEFAULT '0' COMMENT '低详情评分数量',
  `missing_entity_count` int NOT NULL DEFAULT '0' COMMENT '核心实体缺失数量',
  `snapshot_payload` json DEFAULT NULL COMMENT '完整质量报告JSON',
  `snapshot_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '快照时间',
  PRIMARY KEY (`id`),
  KEY `idx_data_quality_category_time` (`category_code`,`snapshot_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='数据质量快照表：保存重复、缺失、低质量等治理指标';

CREATE TABLE IF NOT EXISTS `detail_job` (
  `id` bigint unsigned NOT NULL AUTO_INCREMENT COMMENT '详情补偿任务ID',
  `info_id` bigint unsigned NOT NULL COMMENT '信息ID',
  `channel_code` varchar(50) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT '' COMMENT '渠道编码',
  `status` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'pending' COMMENT '任务状态：pending/running/succeeded/failed/cancelled',
  `priority` int NOT NULL DEFAULT '50' COMMENT '任务优先级，数值越大越优先',
  `attempt_count` int NOT NULL DEFAULT '0' COMMENT '已尝试次数',
  `max_attempts` int NOT NULL DEFAULT '3' COMMENT '最大尝试次数',
  `next_run_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '下次可执行时间',
  `last_failure_reason` varchar(255) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT '' COMMENT '最近失败原因',
  `strategy_hint` varchar(100) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT '' COMMENT '建议使用的详情策略',
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  KEY `idx_detail_job_status_priority` (`status`,`priority`,`next_run_at`),
  KEY `idx_detail_job_channel_status` (`channel_code`,`status`),
  KEY `idx_detail_job_info_status` (`info_id`,`status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='详情补偿任务表：保存低分、失败或列表态内容的二次抓取任务';

CREATE TABLE IF NOT EXISTS `event` (
  `id` bigint unsigned NOT NULL AUTO_INCREMENT COMMENT '事件ID',
  `event_key` varchar(120) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '事件稳定键：用于重建时识别同一热点事件',
  `title` varchar(200) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '事件标题',
  `one_line_summary` varchar(255) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT '' COMMENT '一句话看懂，要求避免与标题重复',
  `primary_category_id` bigint unsigned NOT NULL COMMENT '主分类ID',
  `status` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'active' COMMENT '事件状态：active/archived/hidden',
  `display_quality_score` int NOT NULL DEFAULT '0' COMMENT '展示质量分',
  `display_quality_level` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT '' COMMENT '展示质量等级: excellent/good/weak/blocked',
  `display_quality_reason` varchar(500) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT '' COMMENT '展示质量原因，逗号分隔',
  `heat_score` int NOT NULL DEFAULT '0' COMMENT '热度分',
  `freshness_score` int NOT NULL DEFAULT '0' COMMENT '时效分',
  `composite_score` int NOT NULL DEFAULT '0' COMMENT '综合分',
  `source_count` int NOT NULL DEFAULT '0' COMMENT '来源数量',
  `started_at` datetime DEFAULT NULL COMMENT '事件开始时间',
  `last_updated_at` datetime DEFAULT NULL COMMENT '事件最后更新时间',
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  `previous_event_id` bigint unsigned DEFAULT NULL COMMENT '同实体前序事件ID',
  `event_generation` int unsigned DEFAULT '1' COMMENT '事件代数',
  `evolution_stage` varchar(20) COLLATE utf8mb4_unicode_ci DEFAULT 'emerging' COMMENT '演变阶段: emerging/peak/declining/resolved/recurring',
  PRIMARY KEY (`id`),
  KEY `idx_event_category_score` (`primary_category_id`,`composite_score`,`last_updated_at`),
  KEY `idx_event_status_updated` (`status`,`last_updated_at`),
  KEY `idx_event_core_entity` (`event_key`,`event_generation`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='事件主表：面向用户展示的聚合热点事件';

CREATE TABLE IF NOT EXISTS `event_analysis_run` (
  `id` bigint unsigned NOT NULL AUTO_INCREMENT COMMENT '事件分析运行ID',
  `event_id` bigint unsigned NOT NULL COMMENT '事件ID，由代码约束关联event.id',
  `analysis_version` varchar(30) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'v1' COMMENT '分析版本',
  `mode` varchar(30) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'rule' COMMENT '分析模式：rule/hybrid/llm',
  `provider` varchar(50) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'rule' COMMENT '分析提供方',
  `model_name` varchar(100) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT '' COMMENT '模型名称',
  `status` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'succeeded' COMMENT '运行状态：succeeded/fallback/failed',
  `input_item_count` int NOT NULL DEFAULT '0' COMMENT '输入来源数量',
  `quality_score` decimal(6,2) NOT NULL DEFAULT '0.00' COMMENT '分析质量分',
  `confidence` decimal(5,4) NOT NULL DEFAULT '0.0000' COMMENT '分析置信度',
  `fallback_used` tinyint NOT NULL DEFAULT '0' COMMENT '是否使用规则回退：1是，0否',
  `failure_reason` varchar(500) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT '' COMMENT '失败原因',
  `started_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '开始时间',
  `finished_at` datetime DEFAULT NULL COMMENT '结束时间',
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  PRIMARY KEY (`id`),
  KEY `idx_event_analysis_run_event_time` (`event_id`,`created_at`),
  KEY `idx_event_analysis_run_status` (`status`,`provider`),
  KEY `idx_event_id` (`event_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='事件分析运行表：记录规则或大模型分析的一次完整执行';

CREATE TABLE IF NOT EXISTS `event_analysis_snapshot` (
  `id` bigint unsigned NOT NULL AUTO_INCREMENT COMMENT '事件分析快照ID',
  `event_id` bigint unsigned NOT NULL COMMENT '事件ID，由代码约束关联event.id',
  `run_id` bigint unsigned NOT NULL COMMENT '分析运行ID，由代码约束关联event_analysis_run.id',
  `analysis_type` varchar(50) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '分析类型',
  `content` text COLLATE utf8mb4_unicode_ci COMMENT '分析内容',
  `provider` varchar(50) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'rule' COMMENT '分析提供方',
  `model_name` varchar(100) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT '' COMMENT '模型名称',
  `quality_score` decimal(6,2) NOT NULL DEFAULT '0.00' COMMENT '质量分',
  `confidence` decimal(5,4) NOT NULL DEFAULT '0.0000' COMMENT '置信度',
  `version` int NOT NULL DEFAULT '1' COMMENT '版本号',
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  PRIMARY KEY (`id`),
  KEY `idx_event_analysis_snapshot_lookup` (`event_id`,`analysis_type`,`version`),
  KEY `idx_event_analysis_snapshot_run` (`run_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='事件分析快照表：保存结构化分析输出';

CREATE TABLE IF NOT EXISTS `event_analysis_source` (
  `id` bigint unsigned NOT NULL AUTO_INCREMENT,
  `run_id` bigint unsigned NOT NULL COMMENT '关联的分析运行ID',
  `info_id` bigint unsigned NOT NULL COMMENT 'Info记录ID',
  `info_title` varchar(200) COLLATE utf8mb4_unicode_ci DEFAULT '' COMMENT 'Info标题快照',
  `role` varchar(20) COLLATE utf8mb4_unicode_ci DEFAULT 'media' COMMENT '角色: primary/background/media',
  `weight` int DEFAULT '0' COMMENT '权重分',
  `quality_score` int DEFAULT '0' COMMENT '质量分',
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_run_id` (`run_id`),
  KEY `idx_info_id` (`info_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='事件分析来源记录表';

CREATE TABLE IF NOT EXISTS `event_evolution` (
  `id` bigint unsigned NOT NULL AUTO_INCREMENT,
  `event_id` bigint unsigned NOT NULL COMMENT '当前事件ID',
  `previous_event_id` bigint unsigned DEFAULT NULL COMMENT '前序事件ID',
  `evolution_type` varchar(30) COLLATE utf8mb4_unicode_ci DEFAULT '' COMMENT '演变类型: escalation/expansion/correction/recurrence/none',
  `evolution_summary` text COLLATE utf8mb4_unicode_ci COMMENT '演变摘要: 本事件相比前序事件的增量变化',
  `source_count_delta` int DEFAULT '0' COMMENT '来源数变化(正=增加)',
  `key_change` text COLLATE utf8mb4_unicode_ci COMMENT '关键变化描述',
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_event_evolution_event_id` (`event_id`),
  KEY `idx_event_evolution_previous_event_id` (`previous_event_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='事件演变记录表';

CREATE TABLE IF NOT EXISTS `event_fact_snapshot` (
  `id` bigint unsigned NOT NULL AUTO_INCREMENT COMMENT '事件事实ID',
  `event_id` bigint unsigned NOT NULL COMMENT '事件ID，由代码约束关联event.id',
  `run_id` bigint unsigned NOT NULL COMMENT '分析运行ID，由代码约束关联event_analysis_run.id',
  `fact_type` varchar(50) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '事实类型',
  `content` text COLLATE utf8mb4_unicode_ci COMMENT '事实内容',
  `source_item_id` bigint unsigned DEFAULT NULL COMMENT '来源内容ID，由代码约束关联info.id',
  `confidence` decimal(5,4) NOT NULL DEFAULT '0.0000' COMMENT '事实置信度',
  `evidence` json DEFAULT NULL COMMENT '证据JSON',
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  PRIMARY KEY (`id`),
  KEY `idx_event_fact_event_type` (`event_id`,`fact_type`),
  KEY `idx_event_fact_run` (`run_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='事件事实快照表：保存从来源中抽取的关键事实和证据';

CREATE TABLE IF NOT EXISTS `event_item_link` (
  `id` bigint unsigned NOT NULL AUTO_INCREMENT COMMENT '关联ID',
  `event_id` bigint unsigned NOT NULL COMMENT '事件ID',
  `item_id` bigint unsigned NOT NULL COMMENT '内容项ID',
  `role` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'media' COMMENT '内容角色：primary/media/background',
  `is_primary` tinyint NOT NULL DEFAULT '0' COMMENT '是否主来源：1是，0否',
  `weight` int NOT NULL DEFAULT '0' COMMENT '关联权重',
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_event_item` (`event_id`,`item_id`),
  KEY `idx_event_item_item_id` (`item_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='事件内容关联表：保存事件与原始内容之间的关系';

CREATE TABLE IF NOT EXISTS `event_summary_snapshot` (
  `id` bigint unsigned NOT NULL AUTO_INCREMENT COMMENT '摘要快照ID',
  `event_id` bigint unsigned NOT NULL COMMENT '事件ID',
  `summary_type` varchar(30) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '摘要类型：what_happened/latest_progress/key_takeaway/source_compare',
  `content` text COLLATE utf8mb4_unicode_ci COMMENT '摘要内容',
  `version` int NOT NULL DEFAULT '1' COMMENT '摘要版本号',
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  PRIMARY KEY (`id`),
  KEY `idx_event_summary_lookup` (`event_id`,`summary_type`,`version`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='事件摘要快照表：保存不同类型的事件摘要';

CREATE TABLE IF NOT EXISTS `event_timeline_analysis` (
  `id` bigint unsigned NOT NULL AUTO_INCREMENT COMMENT '事件时间线分析ID',
  `event_id` bigint unsigned NOT NULL COMMENT '事件ID，由代码约束关联event.id',
  `run_id` bigint unsigned NOT NULL COMMENT '分析运行ID，由代码约束关联event_analysis_run.id',
  `occurred_at` datetime NOT NULL COMMENT '节点发生时间',
  `summary` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '节点摘要',
  `source_item_id` bigint unsigned DEFAULT NULL COMMENT '来源内容ID，由代码约束关联info.id',
  `confidence` decimal(5,4) NOT NULL DEFAULT '0.0000' COMMENT '节点置信度',
  `evidence` json DEFAULT NULL COMMENT '证据JSON',
  `display_order` int NOT NULL DEFAULT '0' COMMENT '展示顺序',
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  PRIMARY KEY (`id`),
  KEY `idx_event_timeline_analysis_event_time` (`event_id`,`occurred_at`),
  KEY `idx_event_timeline_analysis_run` (`run_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='事件时间线分析表：保存升级后的时间线节点';

CREATE TABLE IF NOT EXISTS `event_timeline_entry` (
  `id` bigint unsigned NOT NULL AUTO_INCREMENT COMMENT '时间线节点ID',
  `event_id` bigint unsigned NOT NULL COMMENT '事件ID',
  `occurred_at` datetime NOT NULL COMMENT '节点发生时间',
  `summary` varchar(255) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '节点摘要',
  `source_item_id` bigint unsigned NOT NULL COMMENT '来源内容项ID',
  `confidence` decimal(5,4) NOT NULL DEFAULT '0.0000' COMMENT '节点置信度',
  `display_order` int NOT NULL DEFAULT '0' COMMENT '展示顺序',
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `run_id` bigint unsigned DEFAULT NULL COMMENT '关联分析运行ID',
  `evidence` json DEFAULT NULL COMMENT '证据JSON',
  PRIMARY KEY (`id`),
  KEY `idx_event_timeline_event_time` (`event_id`,`occurred_at`),
  KEY `fk_event_timeline_info` (`source_item_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='事件时间线表：保存事件发展脉络';

CREATE TABLE IF NOT EXISTS `info` (
  `id` bigint unsigned NOT NULL AUTO_INCREMENT COMMENT '信息ID',
  `title` varchar(200) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '标题，面向用户展示时建议控制在40字以内',
  `content` mediumtext COLLATE utf8mb4_unicode_ci COMMENT '正文内容或事件详情',
  `category_id` bigint unsigned NOT NULL COMMENT '分类ID',
  `channel_id` bigint unsigned NOT NULL COMMENT '渠道ID',
  `source_id` varchar(100) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT '' COMMENT '来源唯一标识，用于渠道内去重',
  `source_url` varchar(500) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT '' COMMENT '原始来源URL',
  `event_time` datetime DEFAULT NULL COMMENT '事件发生时间或来源发布时间',
  `core_entity` varchar(100) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT '' COMMENT '核心主体、人物、机构或产品',
  `location` varchar(100) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT '' COMMENT '事件地点',
  `indicator_name` varchar(100) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT '' COMMENT '指标名称，经济数据类使用',
  `indicator_value` varchar(100) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT '' COMMENT '指标数值，经济数据类使用',
  `detail_fetch_status` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'pending' COMMENT '详情采集状态：pending/list_only/partial/complete/failed',
  `detail_fetch_error` varchar(500) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT '' COMMENT '详情采集失败原因',
  `detail_strategy` varchar(50) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT '' COMMENT '详情采集策略',
  `detail_score` int NOT NULL DEFAULT '0' COMMENT '详情完整度评分，0-100',
  `detail_content_length` int NOT NULL DEFAULT '0' COMMENT '详情正文长度',
  `detail_fetched_at` datetime DEFAULT NULL COMMENT '详情采集完成时间',
  `tech_topic_type` varchar(50) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT '' COMMENT '科技主题类型，例如编程、大模型、芯片',
  `tech_entities` varchar(500) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT '' COMMENT '科技核心实体，使用逗号分隔',
  `tech_keywords` varchar(500) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT '' COMMENT '科技关键词，使用逗号分隔',
  `is_deleted` tinyint NOT NULL DEFAULT '0' COMMENT '逻辑删除：0正常，1删除',
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_source_channel` (`source_id`,`channel_id`),
  KEY `idx_info_category_id` (`category_id`),
  KEY `idx_info_channel_id` (`channel_id`),
  KEY `idx_info_event_time` (`event_time`),
  KEY `idx_info_created_at` (`created_at`),
  KEY `idx_info_detail_fetch_status` (`detail_fetch_status`),
  KEY `idx_info_deleted_category_time` (`is_deleted`,`category_id`,`event_time`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='信息主表：保存采集到的原始内容和详情质量字段';

CREATE TABLE IF NOT EXISTS `info_acquisition_log` (
  `id` bigint unsigned NOT NULL AUTO_INCREMENT COMMENT '采集日志ID',
  `info_id` bigint unsigned NOT NULL COMMENT '信息ID',
  `channel_code` varchar(50) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT '' COMMENT '渠道编码',
  `strategy` varchar(50) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT '' COMMENT '详情采集策略',
  `status` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT '' COMMENT '采集结果状态',
  `score` int NOT NULL DEFAULT '0' COMMENT '完整度得分',
  `content_length` int NOT NULL DEFAULT '0' COMMENT '正文长度',
  `failure_reason` varchar(255) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT '' COMMENT '失败原因',
  `matched_rules` varchar(500) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT '' COMMENT '命中规则',
  `raw_excerpt` text COLLATE utf8mb4_unicode_ci COMMENT '原始内容摘要',
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  PRIMARY KEY (`id`),
  KEY `idx_info_acquisition_info_created` (`info_id`,`created_at`),
  KEY `idx_info_acquisition_channel_strategy` (`channel_code`,`strategy`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='详情采集日志表：记录单条内容的详情抓取过程';

CREATE TABLE IF NOT EXISTS `llm_call_log` (
  `id` int NOT NULL AUTO_INCREMENT COMMENT '大模型调用日志ID',
  `config_id` int NOT NULL COMMENT '大模型配置ID，由代码约束关联llm_model_config.id',
  `provider_code` varchar(50) NOT NULL COMMENT '供应商编码',
  `model_name` varchar(100) NOT NULL COMMENT '模型名称',
  `status` varchar(20) NOT NULL COMMENT '调用状态: succeeded/failed',
  `latency_ms` int NOT NULL COMMENT '调用耗时毫秒',
  `input_item_count` int NOT NULL COMMENT '输入来源数量',
  `error_message` varchar(500) DEFAULT NULL COMMENT '错误信息',
  `created_at` datetime DEFAULT NULL COMMENT '创建时间',
  `request_payload` json DEFAULT NULL COMMENT '请求参数快照，包含消息内容',
  `response_content` longtext COMMENT '模型返回文本',
  `response_payload` json DEFAULT NULL COMMENT '模型原始响应快照',
  PRIMARY KEY (`id`),
  KEY `idx_llm_call_status_time` (`status`,`created_at`),
  KEY `idx_llm_call_config_time` (`config_id`,`created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE IF NOT EXISTS `llm_model_config` (
  `id` int NOT NULL AUTO_INCREMENT COMMENT '大模型配置ID',
  `provider_name` varchar(50) NOT NULL COMMENT '模型供应商名称',
  `provider_code` varchar(50) NOT NULL COMMENT '模型供应商编码',
  `base_url` varchar(255) NOT NULL COMMENT 'OpenAI兼容接口地址',
  `api_key` varchar(500) DEFAULT NULL COMMENT 'API密钥',
  `model_name` varchar(100) NOT NULL COMMENT '模型名称',
  `is_enabled` int NOT NULL COMMENT '是否启用: 1启用 0停用',
  `daily_call_limit` int NOT NULL COMMENT '每日调用上限，0表示不限',
  `daily_call_count` int NOT NULL COMMENT '当日已调用次数',
  `last_call_date` date DEFAULT NULL COMMENT '最近调用日期',
  `priority` int NOT NULL COMMENT '选择优先级，数值越小越优先',
  `consecutive_failure_count` int NOT NULL COMMENT '连续失败次数，用于自动熔断',
  `circuit_open_until` datetime DEFAULT NULL COMMENT '熔断结束时间，未到期前跳过该模型',
  `last_failure_reason` varchar(500) DEFAULT NULL COMMENT '最近失败原因',
  `created_at` datetime DEFAULT NULL COMMENT '创建时间',
  `updated_at` datetime DEFAULT NULL COMMENT '更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_llm_provider_model` (`provider_code`,`model_name`),
  KEY `idx_llm_enabled_priority` (`is_enabled`,`priority`,`id`),
  KEY `idx_llm_circuit_open_until` (`circuit_open_until`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE IF NOT EXISTS `rebuild_checkpoint` (
  `id` int unsigned NOT NULL AUTO_INCREMENT,
  `checkpoint_type` varchar(30) COLLATE utf8mb4_unicode_ci DEFAULT 'incremental' COMMENT 'incremental / full',
  `max_info_id_processed` int DEFAULT '0' COMMENT '已处理的最大InfoID',
  `max_event_time_processed` datetime DEFAULT NULL COMMENT '已处理的最大事件时间',
  `events_created` int DEFAULT '0' COMMENT '本次新建事件数',
  `events_updated` int DEFAULT '0' COMMENT '本次更新事件数',
  `items_processed` int DEFAULT '0' COMMENT '本次处理Info数',
  `started_at` datetime DEFAULT CURRENT_TIMESTAMP,
  `finished_at` datetime DEFAULT NULL,
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_rebuild_checkpoint_type` (`checkpoint_type`,`created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='事件重建检查点表';

CREATE TABLE IF NOT EXISTS `user_account` (
  `id` bigint unsigned NOT NULL AUTO_INCREMENT COMMENT '用户ID',
  `email` varchar(255) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '邮箱地址，作为当前阶段的注册和登录账号',
  `password_hash` varchar(255) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '密码哈希，使用 bcrypt 或后续统一密码算法',
  `display_name` varchar(80) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT '' COMMENT '用户展示名称',
  `role` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'user' COMMENT '用户角色：user/admin/operator',
  `status` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'active' COMMENT '账号状态：active/disabled/pending',
  `email_verified_at` datetime DEFAULT NULL COMMENT '邮箱验证时间',
  `last_login_at` datetime DEFAULT NULL COMMENT '最近登录时间',
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_user_account_email` (`email`),
  KEY `idx_user_account_role_status` (`role`,`status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='用户账号表：保存邮箱注册用户和管理员账号';

CREATE TABLE IF NOT EXISTS `user_favorite_event` (
  `id` bigint unsigned NOT NULL AUTO_INCREMENT COMMENT '收藏ID',
  `user_id` bigint unsigned NOT NULL COMMENT '用户ID',
  `event_id` bigint unsigned NOT NULL COMMENT '事件ID',
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '收藏时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_user_favorite_event` (`user_id`,`event_id`),
  KEY `idx_user_favorite_event_event` (`event_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='用户事件收藏表：保存登录用户收藏的热点事件';

CREATE TABLE IF NOT EXISTS `user_preference` (
  `id` bigint unsigned NOT NULL AUTO_INCREMENT COMMENT '偏好ID',
  `user_id` bigint unsigned NOT NULL COMMENT '用户ID',
  `preference_key` varchar(80) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '偏好键，例如默认分类、默认排序',
  `preference_value` varchar(500) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT '' COMMENT '偏好值',
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_user_preference_key` (`user_id`,`preference_key`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='用户偏好表：保存登录用户个性化配置';

CREATE TABLE IF NOT EXISTS `user_read_history` (
  `id` bigint unsigned NOT NULL AUTO_INCREMENT COMMENT '阅读历史ID',
  `user_id` bigint unsigned NOT NULL COMMENT '用户ID',
  `event_id` bigint unsigned DEFAULT NULL COMMENT '事件ID',
  `info_id` bigint unsigned DEFAULT NULL COMMENT '信息ID',
  `read_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '阅读时间',
  PRIMARY KEY (`id`),
  KEY `idx_user_read_history_user_time` (`user_id`,`read_at`),
  KEY `fk_user_read_history_event` (`event_id`),
  KEY `fk_user_read_history_info` (`info_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='用户阅读历史表：保存登录用户浏览记录';

CREATE TABLE IF NOT EXISTS `user_session` (
  `id` bigint unsigned NOT NULL AUTO_INCREMENT COMMENT '会话ID',
  `user_id` bigint unsigned NOT NULL COMMENT '用户ID',
  `session_token_hash` char(64) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '会话令牌哈希，避免明文 token 入库',
  `client_type` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'web' COMMENT '客户端类型：web/admin/mobile',
  `ip_address` varchar(64) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT '' COMMENT '登录IP地址',
  `user_agent` varchar(500) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT '' COMMENT '登录设备User-Agent',
  `expires_at` datetime NOT NULL COMMENT '会话过期时间',
  `revoked_at` datetime DEFAULT NULL COMMENT '会话吊销时间',
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_user_session_token_hash` (`session_token_hash`),
  KEY `idx_user_session_user_expires` (`user_id`,`expires_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='用户会话表：保存登录态和管理后台会话';

-- ============================================================
-- 基础启动数据：只包含上线必需配置，不包含业务采集数据和真实凭证
-- ============================================================

-- ------------------------------------------------------------
-- 基础分类初始化
-- ------------------------------------------------------------

INSERT INTO `category` (`name`, `code`, `description`)
VALUES
  ('热点事件', 'hot', '微博、头条、小红书、知乎等平台的热点事件'),
  ('经济数据', 'economy', '金价、油价、汇率、宏观数据等经济指标'),
  ('国际大事', 'international', '国际政治、地缘冲突、外交与全球公共事件'),
  ('科技动向', 'tech', '软件工程、云原生、开发者生态、硬件与互联网科技'),
  ('AI大模型', 'ai', 'AI模型、智能体、多模态、AI产品与产业动态'),
  ('体育赛事', 'sports', '足球、篮球、综合体育赛事与体育新闻')
ON DUPLICATE KEY UPDATE
  `name` = VALUES(`name`),
  `description` = VALUES(`description`),
  `updated_at` = CURRENT_TIMESTAMP;

-- ------------------------------------------------------------
-- Max 当前采集渠道初始化
-- ------------------------------------------------------------

INSERT INTO `channel` (
  `name`, `code`, `base_url`, `category_id`,
  `base_interval_minutes`, `hot_interval_minutes`, `min_interval_minutes`,
  `max_interval_minutes`, `manual_interval_enabled`, `effective_interval_minutes`,
  `schedule_version`, `is_active`
)
VALUES
  ('微博', 'weibo', 'https://weibo.com', (SELECT `id` FROM `category` WHERE `code` = 'hot'), 30, 10, 3, 120, 1, 30, 1, 1),
  ('今日头条', 'toutiao', 'https://www.toutiao.com', (SELECT `id` FROM `category` WHERE `code` = 'hot'), 30, 10, 3, 120, 1, 30, 1, 1),
  ('小红书', 'xiaohongshu', 'https://www.xiaohongshu.com', (SELECT `id` FROM `category` WHERE `code` = 'hot'), 30, 10, 3, 120, 1, 30, 1, 1),
  ('知乎', 'zhihu', 'https://www.zhihu.com', (SELECT `id` FROM `category` WHERE `code` = 'ai'), 60, 10, 10, 240, 1, 60, 1, 1),
  ('东方财富网', 'eastmoney', 'https://www.eastmoney.com', (SELECT `id` FROM `category` WHERE `code` = 'economy'), 60, 10, 10, 240, 1, 60, 1, 1),
  ('路透社', 'reuters', 'https://www.reuters.com', (SELECT `id` FROM `category` WHERE `code` = 'international'), 120, 10, 10, 480, 1, 120, 1, 1),
  ('CSDN', 'csdn', 'https://blog.csdn.net', (SELECT `id` FROM `category` WHERE `code` = 'tech'), 120, 10, 10, 480, 1, 120, 1, 1),
  ('掘金', 'juejin', 'https://juejin.cn', (SELECT `id` FROM `category` WHERE `code` = 'tech'), 120, 10, 10, 480, 1, 120, 1, 1),
  ('博客园', 'cnblogs', 'https://www.cnblogs.com', (SELECT `id` FROM `category` WHERE `code` = 'tech'), 120, 10, 10, 480, 1, 120, 1, 1),
  ('36氪', '36kr', 'https://36kr.com', (SELECT `id` FROM `category` WHERE `code` = 'ai'), 120, 10, 10, 480, 1, 120, 1, 1),
  ('央视体育网', 'cctv_sports', 'https://sports.cctv.com', (SELECT `id` FROM `category` WHERE `code` = 'sports'), 60, 10, 10, 240, 1, 60, 1, 1),
  ('新浪体育', 'sina_sports', 'https://sports.sina.com.cn', (SELECT `id` FROM `category` WHERE `code` = 'sports'), 60, 10, 10, 240, 1, 60, 1, 1)
ON DUPLICATE KEY UPDATE
  `name` = VALUES(`name`),
  `base_url` = VALUES(`base_url`),
  `category_id` = VALUES(`category_id`),
  `base_interval_minutes` = VALUES(`base_interval_minutes`),
  `hot_interval_minutes` = VALUES(`hot_interval_minutes`),
  `min_interval_minutes` = VALUES(`min_interval_minutes`),
  `max_interval_minutes` = VALUES(`max_interval_minutes`),
  `manual_interval_enabled` = VALUES(`manual_interval_enabled`),
  `effective_interval_minutes` = VALUES(`effective_interval_minutes`),
  `schedule_version` = GREATEST(`schedule_version`, VALUES(`schedule_version`)),
  `is_active` = VALUES(`is_active`),
  `updated_at` = CURRENT_TIMESTAMP;

-- ------------------------------------------------------------
-- 渠道凭证格式样例：只用于管理后台展示和格式校验参考
-- status=sample 的记录不会被采集器作为有效登录态读取。
-- 真实 Cookie / ZSE 请在管理后台“凭证管理”中保存，保存后状态会变为 active。
-- ------------------------------------------------------------

UPDATE `channel`
SET
  `cookies` = JSON_OBJECT(
    'cookie', 'SUB=sample_weibo_sub; XSRF-TOKEN=sample_csrf_token',
    'status', 'sample',
    'last_verified_at', CAST(NULL AS CHAR),
    'note', '格式样例，不会被采集器作为有效凭证读取；请在管理后台替换为真实 Cookie。'
  ),
  `credentials_updated_at` = COALESCE(`credentials_updated_at`, CURRENT_TIMESTAMP),
  `credentials_updated_by` = IF(COALESCE(`credentials_updated_by`, '') = '', 'seed_sample', `credentials_updated_by`)
WHERE `code` = 'weibo'
  AND (
    COALESCE(`cookies`, '') = ''
    OR (JSON_VALID(`cookies`) AND JSON_UNQUOTE(JSON_EXTRACT(`cookies`, '$.status')) = 'sample')
  );

UPDATE `channel`
SET
  `cookies` = JSON_OBJECT(
    'cookie', 'z_c0=sample_z_c0; d_c0=sample_d_c0; _xsrf=sample_xsrf',
    'status', 'sample',
    'last_verified_at', CAST(NULL AS CHAR),
    'note', '格式样例，不会被采集器作为有效凭证读取；请在管理后台替换为真实 Cookie。'
  ),
  `extra_credentials` = JSON_OBJECT(
    'zhihu', JSON_OBJECT(
      'zse_93', '101_3_3.0',
      'zse_96', '2.0_sample_signature',
      'status', 'sample',
      'note', '格式样例，不会被采集器作为有效 ZSE 头读取。'
    )
  ),
  `credentials_updated_at` = COALESCE(`credentials_updated_at`, CURRENT_TIMESTAMP),
  `credentials_updated_by` = IF(COALESCE(`credentials_updated_by`, '') = '', 'seed_sample', `credentials_updated_by`)
WHERE `code` = 'zhihu'
  AND (
    COALESCE(`cookies`, '') = ''
    OR (JSON_VALID(`cookies`) AND JSON_UNQUOTE(JSON_EXTRACT(`cookies`, '$.status')) = 'sample')
  );

UPDATE `channel`
SET
  `cookies` = JSON_OBJECT(
    'cookie', 'a1=sample_a1; web_session=sample_web_session; webId=sample_web_id',
    'status', 'sample',
    'last_verified_at', CAST(NULL AS CHAR),
    'note', '格式样例，不会被采集器作为有效凭证读取；请在管理后台替换为真实 Cookie。'
  ),
  `credentials_updated_at` = COALESCE(`credentials_updated_at`, CURRENT_TIMESTAMP),
  `credentials_updated_by` = IF(COALESCE(`credentials_updated_by`, '') = '', 'seed_sample', `credentials_updated_by`)
WHERE `code` = 'xiaohongshu'
  AND (
    COALESCE(`cookies`, '') = ''
    OR (JSON_VALID(`cookies`) AND JSON_UNQUOTE(JSON_EXTRACT(`cookies`, '$.status')) = 'sample')
  );

-- ------------------------------------------------------------
-- 采集任务初始化：每个启用渠道一条 interval 任务
-- ------------------------------------------------------------

INSERT INTO `crawl_task` (
  `channel_id`, `task_code`, `task_name`, `schedule_type`,
  `schedule_value`, `schedule_version`, `status`, `next_run_at`
)
SELECT
  ch.`id`,
  CONCAT(ch.`code`, '_interval_crawl'),
  CONCAT(ch.`name`, '定时采集'),
  'interval',
  CAST(ch.`effective_interval_minutes` AS CHAR),
  ch.`schedule_version`,
  CASE WHEN ch.`is_active` = 1 THEN 'active' ELSE 'disabled' END,
  CURRENT_TIMESTAMP
FROM `channel` AS ch
ON DUPLICATE KEY UPDATE
  `channel_id` = VALUES(`channel_id`),
  `task_name` = VALUES(`task_name`),
  `schedule_type` = VALUES(`schedule_type`),
  `schedule_value` = VALUES(`schedule_value`),
  `schedule_version` = VALUES(`schedule_version`),
  `status` = VALUES(`status`),
  `next_run_at` = COALESCE(`next_run_at`, CURRENT_TIMESTAMP),
  `updated_at` = CURRENT_TIMESTAMP;

-- ------------------------------------------------------------
-- 默认管理员初始化
-- 默认密码 Admin123456。生产环境首次登录后必须修改。
-- ------------------------------------------------------------

INSERT INTO `user_account` (`email`, `password_hash`, `display_name`, `role`, `status`, `email_verified_at`)
VALUES (
  'admin@info-daren.local',
  'pbkdf2_sha256$210000$NXiTL/HJ37ndl7tJUadNUQ$HXhBu0gh3QNYIwlAwq/dYEmvJrTcu8aa4oArWZJZS9Y',
  '系统管理员',
  'admin',
  'active',
  CURRENT_TIMESTAMP
)
ON DUPLICATE KEY UPDATE
  `role` = 'admin',
  `status` = 'active',
  `display_name` = IF(`display_name` = '', VALUES(`display_name`), `display_name`),
  `updated_at` = CURRENT_TIMESTAMP;

-- ------------------------------------------------------------
-- 初始治理快照：让管理端空库时有全局质量基线记录
-- ------------------------------------------------------------

INSERT INTO `data_quality_snapshot` (
  `category_code`, `total_count`, `duplicate_title_count`,
  `empty_content_count`, `low_detail_score_count`, `missing_entity_count`,
  `snapshot_payload`, `snapshot_at`
)
SELECT
  'all',
  stats.`total_count`,
  0,
  stats.`empty_content_count`,
  stats.`low_detail_score_count`,
  stats.`missing_entity_count`,
  JSON_OBJECT('source', 'mysql8_init', 'created_by', 'init', 'note', 'initial quality baseline'),
  CURRENT_TIMESTAMP
FROM (
  SELECT
    COUNT(*) AS `total_count`,
    COALESCE(SUM(CASE WHEN COALESCE(`content`, '') = '' THEN 1 ELSE 0 END), 0) AS `empty_content_count`,
    COALESCE(SUM(CASE WHEN `detail_score` < 60 THEN 1 ELSE 0 END), 0) AS `low_detail_score_count`,
    COALESCE(SUM(CASE WHEN COALESCE(`core_entity`, '') = '' THEN 1 ELSE 0 END), 0) AS `missing_entity_count`
  FROM `info`
) AS stats
WHERE NOT EXISTS (
  SELECT 1
  FROM `data_quality_snapshot`
  WHERE `category_code` = 'all'
);

-- ------------------------------------------------------------
-- 默认大模型配置：默认关闭，管理端填写 API Key 后启用
-- ------------------------------------------------------------

INSERT INTO `llm_model_config` (
  `provider_name`, `provider_code`, `base_url`, `api_key`, `model_name`,
  `is_enabled`, `daily_call_limit`, `daily_call_count`, `last_call_date`, `priority`,
  `consecutive_failure_count`, `circuit_open_until`, `last_failure_reason`
)
VALUES
  ('千问', 'qwen', 'http://127.0.0.1:8001/v1', '', 'qwen2.5-14b-instruct', 0, 1000, 0, CURRENT_DATE, 10, 0, NULL, ''),
  ('DeepSeek', 'deepseek', 'https://api.deepseek.com/v1', '', 'deepseek-chat', 0, 1000, 0, CURRENT_DATE, 20, 0, NULL, '')
ON DUPLICATE KEY UPDATE
  `provider_name` = VALUES(`provider_name`),
  `base_url` = VALUES(`base_url`),
  `daily_call_limit` = VALUES(`daily_call_limit`),
  `consecutive_failure_count` = 0,
  `circuit_open_until` = NULL,
  `last_failure_reason` = '',
  `priority` = VALUES(`priority`),
  `updated_at` = CURRENT_TIMESTAMP;

-- ------------------------------------------------------------
-- 初始化完成检查
-- ------------------------------------------------------------

SELECT 'category' AS `table_name`, COUNT(*) AS `row_count` FROM `category`
UNION ALL
SELECT 'channel', COUNT(*) FROM `channel`
UNION ALL
SELECT 'crawl_task', COUNT(*) FROM `crawl_task`
UNION ALL
SELECT 'user_account', COUNT(*) FROM `user_account`
UNION ALL
SELECT 'llm_model_config', COUNT(*) FROM `llm_model_config`;

SET FOREIGN_KEY_CHECKS = 1;
