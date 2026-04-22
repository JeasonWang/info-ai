-- 信息达人 Pro 版本 MySQL 建表语句
-- 目标数据库：MySQL 8.x
-- 说明：所有业务字段保留中文注释，便于后续维护、迁移和管理后台展示。

CREATE DATABASE IF NOT EXISTS `info-max`
  DEFAULT CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

USE `info-max`;

CREATE TABLE IF NOT EXISTS `category` (
  `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '分类ID',
  `name` VARCHAR(50) NOT NULL COMMENT '分类名称',
  `code` VARCHAR(50) NOT NULL COMMENT '分类编码',
  `description` VARCHAR(200) NOT NULL DEFAULT '' COMMENT '分类描述',
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_category_name` (`name`),
  UNIQUE KEY `uk_category_code` (`code`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='分类表：保存热点、科技、体育等内容分类';

CREATE TABLE IF NOT EXISTS `channel` (
  `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '渠道ID',
  `name` VARCHAR(50) NOT NULL COMMENT '渠道名称',
  `code` VARCHAR(50) NOT NULL COMMENT '渠道编码',
  `base_url` VARCHAR(255) NOT NULL DEFAULT '' COMMENT '渠道基础URL',
  `category_id` BIGINT UNSIGNED NOT NULL COMMENT '关联分类ID',
  `crawl_interval` INT NOT NULL DEFAULT 60 COMMENT '采集间隔，单位分钟',
  `is_active` TINYINT NOT NULL DEFAULT 1 COMMENT '是否启用：1启用，0停用',
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_channel_name` (`name`),
  UNIQUE KEY `uk_channel_code` (`code`),
  KEY `idx_channel_category` (`category_id`),
  CONSTRAINT `fk_channel_category` FOREIGN KEY (`category_id`) REFERENCES `category` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='渠道表：保存微博、央视体育网、CSDN等采集来源';

CREATE TABLE IF NOT EXISTS `info` (
  `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '信息ID',
  `title` VARCHAR(200) NOT NULL COMMENT '标题，面向用户展示时建议控制在40字以内',
  `content` MEDIUMTEXT NULL COMMENT '正文内容或事件详情',
  `category_id` BIGINT UNSIGNED NOT NULL COMMENT '分类ID',
  `channel_id` BIGINT UNSIGNED NOT NULL COMMENT '渠道ID',
  `source_id` VARCHAR(100) NOT NULL DEFAULT '' COMMENT '来源唯一标识，用于渠道内去重',
  `source_url` VARCHAR(500) NOT NULL DEFAULT '' COMMENT '原始来源URL',
  `event_time` DATETIME NULL COMMENT '事件发生时间或来源发布时间',
  `core_entity` VARCHAR(100) NOT NULL DEFAULT '' COMMENT '核心主体、人物、机构或产品',
  `location` VARCHAR(100) NOT NULL DEFAULT '' COMMENT '事件地点',
  `indicator_name` VARCHAR(100) NOT NULL DEFAULT '' COMMENT '指标名称，经济数据类使用',
  `indicator_value` VARCHAR(100) NOT NULL DEFAULT '' COMMENT '指标数值，经济数据类使用',
  `detail_fetch_status` VARCHAR(20) NOT NULL DEFAULT 'pending' COMMENT '详情采集状态：pending/list_only/partial/complete/failed',
  `detail_fetch_error` VARCHAR(500) NOT NULL DEFAULT '' COMMENT '详情采集失败原因',
  `detail_strategy` VARCHAR(50) NOT NULL DEFAULT '' COMMENT '详情采集策略',
  `detail_score` INT NOT NULL DEFAULT 0 COMMENT '详情完整度评分，0-100',
  `detail_content_length` INT NOT NULL DEFAULT 0 COMMENT '详情正文长度',
  `detail_fetched_at` DATETIME NULL COMMENT '详情采集完成时间',
  `tech_topic_type` VARCHAR(50) NOT NULL DEFAULT '' COMMENT '科技主题类型，例如编程、大模型、芯片',
  `tech_entities` VARCHAR(500) NOT NULL DEFAULT '' COMMENT '科技核心实体，使用逗号分隔',
  `tech_keywords` VARCHAR(500) NOT NULL DEFAULT '' COMMENT '科技关键词，使用逗号分隔',
  `is_deleted` TINYINT NOT NULL DEFAULT 0 COMMENT '逻辑删除：0正常，1删除',
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_source_channel` (`source_id`, `channel_id`),
  KEY `idx_info_category_id` (`category_id`),
  KEY `idx_info_channel_id` (`channel_id`),
  KEY `idx_info_event_time` (`event_time`),
  KEY `idx_info_created_at` (`created_at`),
  KEY `idx_info_detail_fetch_status` (`detail_fetch_status`),
  KEY `idx_info_deleted_category_time` (`is_deleted`, `category_id`, `event_time`),
  CONSTRAINT `fk_info_category` FOREIGN KEY (`category_id`) REFERENCES `category` (`id`),
  CONSTRAINT `fk_info_channel` FOREIGN KEY (`channel_id`) REFERENCES `channel` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='信息主表：保存采集到的原始内容和详情质量字段';

CREATE TABLE IF NOT EXISTS `info_acquisition_log` (
  `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '采集日志ID',
  `info_id` BIGINT UNSIGNED NOT NULL COMMENT '信息ID',
  `channel_code` VARCHAR(50) NOT NULL DEFAULT '' COMMENT '渠道编码',
  `strategy` VARCHAR(50) NOT NULL DEFAULT '' COMMENT '详情采集策略',
  `status` VARCHAR(20) NOT NULL DEFAULT '' COMMENT '采集结果状态',
  `score` INT NOT NULL DEFAULT 0 COMMENT '完整度得分',
  `content_length` INT NOT NULL DEFAULT 0 COMMENT '正文长度',
  `failure_reason` VARCHAR(255) NOT NULL DEFAULT '' COMMENT '失败原因',
  `matched_rules` VARCHAR(500) NOT NULL DEFAULT '' COMMENT '命中规则',
  `raw_excerpt` TEXT NULL COMMENT '原始内容摘要',
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  PRIMARY KEY (`id`),
  KEY `idx_info_acquisition_info_created` (`info_id`, `created_at`),
  KEY `idx_info_acquisition_channel_strategy` (`channel_code`, `strategy`),
  CONSTRAINT `fk_info_acquisition_info` FOREIGN KEY (`info_id`) REFERENCES `info` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='详情采集日志表：记录单条内容的详情抓取过程';

CREATE TABLE IF NOT EXISTS `event` (
  `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '事件ID',
  `title` VARCHAR(200) NOT NULL COMMENT '事件标题',
  `one_line_summary` VARCHAR(255) NOT NULL DEFAULT '' COMMENT '一句话看懂，要求避免与标题重复',
  `primary_category_id` BIGINT UNSIGNED NOT NULL COMMENT '主分类ID',
  `status` VARCHAR(20) NOT NULL DEFAULT 'active' COMMENT '事件状态：active/archived/hidden',
  `heat_score` INT NOT NULL DEFAULT 0 COMMENT '热度分',
  `freshness_score` INT NOT NULL DEFAULT 0 COMMENT '时效分',
  `composite_score` INT NOT NULL DEFAULT 0 COMMENT '综合分',
  `source_count` INT NOT NULL DEFAULT 0 COMMENT '来源数量',
  `started_at` DATETIME NULL COMMENT '事件开始时间',
  `last_updated_at` DATETIME NULL COMMENT '事件最后更新时间',
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  KEY `idx_event_category_score` (`primary_category_id`, `composite_score`, `last_updated_at`),
  KEY `idx_event_status_updated` (`status`, `last_updated_at`),
  CONSTRAINT `fk_event_category` FOREIGN KEY (`primary_category_id`) REFERENCES `category` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='事件主表：面向用户展示的聚合热点事件';

CREATE TABLE IF NOT EXISTS `event_item_link` (
  `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '关联ID',
  `event_id` BIGINT UNSIGNED NOT NULL COMMENT '事件ID',
  `item_id` BIGINT UNSIGNED NOT NULL COMMENT '内容项ID',
  `role` VARCHAR(20) NOT NULL DEFAULT 'media' COMMENT '内容角色：primary/media/background',
  `is_primary` TINYINT NOT NULL DEFAULT 0 COMMENT '是否主来源：1是，0否',
  `weight` INT NOT NULL DEFAULT 0 COMMENT '关联权重',
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_event_item` (`event_id`, `item_id`),
  KEY `idx_event_item_item_id` (`item_id`),
  CONSTRAINT `fk_event_item_event` FOREIGN KEY (`event_id`) REFERENCES `event` (`id`),
  CONSTRAINT `fk_event_item_info` FOREIGN KEY (`item_id`) REFERENCES `info` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='事件内容关联表：保存事件与原始内容之间的关系';

CREATE TABLE IF NOT EXISTS `event_timeline_entry` (
  `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '时间线节点ID',
  `event_id` BIGINT UNSIGNED NOT NULL COMMENT '事件ID',
  `occurred_at` DATETIME NOT NULL COMMENT '节点发生时间',
  `summary` VARCHAR(255) NOT NULL COMMENT '节点摘要',
  `source_item_id` BIGINT UNSIGNED NOT NULL COMMENT '来源内容项ID',
  `confidence` DECIMAL(5,4) NOT NULL DEFAULT 0.0000 COMMENT '节点置信度',
  `display_order` INT NOT NULL DEFAULT 0 COMMENT '展示顺序',
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  PRIMARY KEY (`id`),
  KEY `idx_event_timeline_event_time` (`event_id`, `occurred_at`),
  CONSTRAINT `fk_event_timeline_event` FOREIGN KEY (`event_id`) REFERENCES `event` (`id`),
  CONSTRAINT `fk_event_timeline_info` FOREIGN KEY (`source_item_id`) REFERENCES `info` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='事件时间线表：保存事件发展脉络';

CREATE TABLE IF NOT EXISTS `event_summary_snapshot` (
  `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '摘要快照ID',
  `event_id` BIGINT UNSIGNED NOT NULL COMMENT '事件ID',
  `summary_type` VARCHAR(30) NOT NULL COMMENT '摘要类型：what_happened/latest_progress/key_takeaway/source_compare',
  `content` TEXT NULL COMMENT '摘要内容',
  `version` INT NOT NULL DEFAULT 1 COMMENT '摘要版本号',
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  PRIMARY KEY (`id`),
  KEY `idx_event_summary_lookup` (`event_id`, `summary_type`, `version`),
  CONSTRAINT `fk_event_summary_event` FOREIGN KEY (`event_id`) REFERENCES `event` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='事件摘要快照表：保存不同类型的事件摘要';

CREATE TABLE IF NOT EXISTS `user_account` (
  `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '用户ID',
  `email` VARCHAR(255) NOT NULL COMMENT '邮箱地址，作为当前阶段的注册和登录账号',
  `password_hash` VARCHAR(255) NOT NULL COMMENT '密码哈希，使用 bcrypt 或后续统一密码算法',
  `display_name` VARCHAR(80) NOT NULL DEFAULT '' COMMENT '用户展示名称',
  `role` VARCHAR(20) NOT NULL DEFAULT 'user' COMMENT '用户角色：user/admin/operator',
  `status` VARCHAR(20) NOT NULL DEFAULT 'active' COMMENT '账号状态：active/disabled/pending',
  `email_verified_at` DATETIME NULL COMMENT '邮箱验证时间',
  `last_login_at` DATETIME NULL COMMENT '最近登录时间',
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_user_account_email` (`email`),
  KEY `idx_user_account_role_status` (`role`, `status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='用户账号表：保存邮箱注册用户和管理员账号';

CREATE TABLE IF NOT EXISTS `user_session` (
  `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '会话ID',
  `user_id` BIGINT UNSIGNED NOT NULL COMMENT '用户ID',
  `session_token_hash` CHAR(64) NOT NULL COMMENT '会话令牌哈希，避免明文 token 入库',
  `client_type` VARCHAR(20) NOT NULL DEFAULT 'web' COMMENT '客户端类型：web/admin/mobile',
  `ip_address` VARCHAR(64) NOT NULL DEFAULT '' COMMENT '登录IP地址',
  `user_agent` VARCHAR(500) NOT NULL DEFAULT '' COMMENT '登录设备User-Agent',
  `expires_at` DATETIME NOT NULL COMMENT '会话过期时间',
  `revoked_at` DATETIME NULL COMMENT '会话吊销时间',
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_user_session_token_hash` (`session_token_hash`),
  KEY `idx_user_session_user_expires` (`user_id`, `expires_at`),
  CONSTRAINT `fk_user_session_user` FOREIGN KEY (`user_id`) REFERENCES `user_account` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='用户会话表：保存登录态和管理后台会话';

CREATE TABLE IF NOT EXISTS `user_favorite_event` (
  `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '收藏ID',
  `user_id` BIGINT UNSIGNED NOT NULL COMMENT '用户ID',
  `event_id` BIGINT UNSIGNED NOT NULL COMMENT '事件ID',
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '收藏时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_user_favorite_event` (`user_id`, `event_id`),
  KEY `idx_user_favorite_event_event` (`event_id`),
  CONSTRAINT `fk_user_favorite_user` FOREIGN KEY (`user_id`) REFERENCES `user_account` (`id`),
  CONSTRAINT `fk_user_favorite_event` FOREIGN KEY (`event_id`) REFERENCES `event` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='用户事件收藏表：保存登录用户收藏的热点事件';

CREATE TABLE IF NOT EXISTS `user_follow_keyword` (
  `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '关注关键词ID',
  `user_id` BIGINT UNSIGNED NOT NULL COMMENT '用户ID',
  `keyword` VARCHAR(100) NOT NULL COMMENT '关注关键词',
  `category_code` VARCHAR(50) NOT NULL DEFAULT 'all' COMMENT '关键词所属分类编码，all表示全局',
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_user_follow_keyword` (`user_id`, `keyword`, `category_code`),
  CONSTRAINT `fk_user_follow_keyword_user` FOREIGN KEY (`user_id`) REFERENCES `user_account` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='用户关键词关注表：保存登录用户关注主题';

CREATE TABLE IF NOT EXISTS `user_preference` (
  `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '偏好ID',
  `user_id` BIGINT UNSIGNED NOT NULL COMMENT '用户ID',
  `preference_key` VARCHAR(80) NOT NULL COMMENT '偏好键，例如默认分类、默认排序',
  `preference_value` VARCHAR(500) NOT NULL DEFAULT '' COMMENT '偏好值',
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_user_preference_key` (`user_id`, `preference_key`),
  CONSTRAINT `fk_user_preference_user` FOREIGN KEY (`user_id`) REFERENCES `user_account` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='用户偏好表：保存登录用户个性化配置';

CREATE TABLE IF NOT EXISTS `user_read_history` (
  `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '阅读历史ID',
  `user_id` BIGINT UNSIGNED NOT NULL COMMENT '用户ID',
  `event_id` BIGINT UNSIGNED NULL COMMENT '事件ID',
  `info_id` BIGINT UNSIGNED NULL COMMENT '信息ID',
  `read_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '阅读时间',
  PRIMARY KEY (`id`),
  KEY `idx_user_read_history_user_time` (`user_id`, `read_at`),
  CONSTRAINT `fk_user_read_history_user` FOREIGN KEY (`user_id`) REFERENCES `user_account` (`id`),
  CONSTRAINT `fk_user_read_history_event` FOREIGN KEY (`event_id`) REFERENCES `event` (`id`),
  CONSTRAINT `fk_user_read_history_info` FOREIGN KEY (`info_id`) REFERENCES `info` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='用户阅读历史表：保存登录用户浏览记录';

CREATE TABLE IF NOT EXISTS `admin_audit_log` (
  `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '管理后台操作审计日志ID',
  `admin_user_id` BIGINT UNSIGNED NOT NULL COMMENT '管理员用户ID',
  `action` VARCHAR(80) NOT NULL COMMENT '操作动作',
  `target_type` VARCHAR(80) NOT NULL DEFAULT '' COMMENT '操作对象类型',
  `target_id` VARCHAR(80) NOT NULL DEFAULT '' COMMENT '操作对象ID',
  `request_payload` JSON NULL COMMENT '请求参数快照',
  `ip_address` VARCHAR(64) NOT NULL DEFAULT '' COMMENT '操作IP地址',
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  PRIMARY KEY (`id`),
  KEY `idx_admin_audit_user_time` (`admin_user_id`, `created_at`),
  KEY `idx_admin_audit_action_time` (`action`, `created_at`),
  CONSTRAINT `fk_admin_audit_user` FOREIGN KEY (`admin_user_id`) REFERENCES `user_account` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='管理后台审计表：记录管理员关键操作';

CREATE TABLE IF NOT EXISTS `crawl_task` (
  `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '采集任务ID',
  `channel_id` BIGINT UNSIGNED NOT NULL COMMENT '渠道ID',
  `task_code` VARCHAR(80) NOT NULL COMMENT '任务编码',
  `task_name` VARCHAR(100) NOT NULL COMMENT '任务名称',
  `schedule_type` VARCHAR(20) NOT NULL DEFAULT 'interval' COMMENT '调度类型：interval/manual/cron',
  `schedule_value` VARCHAR(100) NOT NULL DEFAULT '' COMMENT '调度配置值',
  `status` VARCHAR(20) NOT NULL DEFAULT 'active' COMMENT '任务状态：active/paused/disabled',
  `last_run_at` DATETIME NULL COMMENT '最近运行时间',
  `next_run_at` DATETIME NULL COMMENT '下次计划运行时间',
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_crawl_task_code` (`task_code`),
  KEY `idx_crawl_task_channel_status` (`channel_id`, `status`),
  CONSTRAINT `fk_crawl_task_channel` FOREIGN KEY (`channel_id`) REFERENCES `channel` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='采集任务表：保存可调度的数据采集任务';

CREATE TABLE IF NOT EXISTS `crawl_run_log` (
  `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '采集运行日志ID',
  `task_id` BIGINT UNSIGNED NULL COMMENT '采集任务ID',
  `channel_code` VARCHAR(50) NOT NULL COMMENT '渠道编码',
  `trigger_type` VARCHAR(20) NOT NULL DEFAULT 'scheduler' COMMENT '触发方式：scheduler/manual/retry',
  `status` VARCHAR(20) NOT NULL COMMENT '运行状态：success/partial/failed',
  `raw_count` INT NOT NULL DEFAULT 0 COMMENT '原始抓取数量',
  `cleaned_count` INT NOT NULL DEFAULT 0 COMMENT '清洗后数量',
  `saved_count` INT NOT NULL DEFAULT 0 COMMENT '入库数量',
  `detail_success_count` INT NOT NULL DEFAULT 0 COMMENT '详情成功数量',
  `detail_failed_count` INT NOT NULL DEFAULT 0 COMMENT '详情失败数量',
  `error_message` VARCHAR(1000) NOT NULL DEFAULT '' COMMENT '错误信息',
  `started_at` DATETIME NOT NULL COMMENT '开始时间',
  `finished_at` DATETIME NULL COMMENT '结束时间',
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  PRIMARY KEY (`id`),
  KEY `idx_crawl_run_channel_time` (`channel_code`, `started_at`),
  KEY `idx_crawl_run_task_time` (`task_id`, `started_at`),
  CONSTRAINT `fk_crawl_run_task` FOREIGN KEY (`task_id`) REFERENCES `crawl_task` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='采集运行日志表：记录每次采集执行结果';

CREATE TABLE IF NOT EXISTS `crawl_health_snapshot` (
  `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '采集健康快照ID',
  `channel_code` VARCHAR(50) NOT NULL COMMENT '渠道编码',
  `success_rate` DECIMAL(5,2) NOT NULL DEFAULT 0.00 COMMENT '最近采集成功率',
  `detail_complete_rate` DECIMAL(5,2) NOT NULL DEFAULT 0.00 COMMENT '详情完整率',
  `avg_detail_score` DECIMAL(5,2) NOT NULL DEFAULT 0.00 COMMENT '平均详情质量分',
  `last_success_at` DATETIME NULL COMMENT '最近成功时间',
  `last_failed_at` DATETIME NULL COMMENT '最近失败时间',
  `snapshot_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '快照时间',
  PRIMARY KEY (`id`),
  KEY `idx_crawl_health_channel_time` (`channel_code`, `snapshot_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='采集健康快照表：保存渠道采集稳定性指标';

CREATE TABLE IF NOT EXISTS `data_quality_snapshot` (
  `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '质量快照ID',
  `category_code` VARCHAR(50) NOT NULL DEFAULT 'all' COMMENT '分类编码，all表示全局',
  `total_count` INT NOT NULL DEFAULT 0 COMMENT '总内容数量',
  `duplicate_title_count` INT NOT NULL DEFAULT 0 COMMENT '重复标题数量',
  `empty_content_count` INT NOT NULL DEFAULT 0 COMMENT '正文为空数量',
  `low_detail_score_count` INT NOT NULL DEFAULT 0 COMMENT '低详情评分数量',
  `missing_entity_count` INT NOT NULL DEFAULT 0 COMMENT '核心实体缺失数量',
  `snapshot_payload` JSON NULL COMMENT '完整质量报告JSON',
  `snapshot_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '快照时间',
  PRIMARY KEY (`id`),
  KEY `idx_data_quality_category_time` (`category_code`, `snapshot_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='数据质量快照表：保存重复、缺失、低质量等治理指标';
