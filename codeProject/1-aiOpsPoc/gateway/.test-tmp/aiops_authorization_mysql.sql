-- Generated from the AIOps SQLite authorization database.
SET NAMES utf8mb4;
CREATE DATABASE IF NOT EXISTS `aiops`
  CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;
USE `aiops`;

CREATE TABLE IF NOT EXISTS `applications` (
  `application_code` VARCHAR(100) NOT NULL,
  `display_name` VARCHAR(255) NOT NULL,
  `enabled` TINYINT(1) NOT NULL DEFAULT 1,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`application_code`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE IF NOT EXISTS `application_aliases` (
  `alias` VARCHAR(255) NOT NULL,
  `application_code` VARCHAR(100) NOT NULL,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`alias`),
  CONSTRAINT `fk_alias_application`
    FOREIGN KEY (`application_code`) REFERENCES `applications` (`application_code`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE IF NOT EXISTS `alert_rule_applications` (
  `alert_name` VARCHAR(255) NOT NULL,
  `application_code` VARCHAR(100) NOT NULL,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`alert_name`),
  CONSTRAINT `fk_rule_application`
    FOREIGN KEY (`application_code`) REFERENCES `applications` (`application_code`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE IF NOT EXISTS `user_roles` (
  `username` VARCHAR(255) NOT NULL,
  `role` ENUM('admin', 'user') NOT NULL,
  `enabled` TINYINT(1) NOT NULL DEFAULT 1,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`username`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE IF NOT EXISTS `user_application_permissions` (
  `username` VARCHAR(255) NOT NULL,
  `application_code` VARCHAR(100) NOT NULL,
  `granted_by` VARCHAR(255) NOT NULL DEFAULT 'admin',
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`username`, `application_code`),
  KEY `idx_user_application_permissions_app` (`application_code`),
  CONSTRAINT `fk_permission_user`
    FOREIGN KEY (`username`) REFERENCES `user_roles` (`username`) ON DELETE CASCADE,
  CONSTRAINT `fk_permission_application`
    FOREIGN KEY (`application_code`) REFERENCES `applications` (`application_code`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- applications: 7 row(s)
INSERT INTO `applications` (`application_code`, `display_name`, `enabled`, `created_at`) VALUES ('iwe', 'iWE', 1, '2026-08-06 02:17:48') ON DUPLICATE KEY UPDATE `application_code` = VALUES(`application_code`), `display_name` = VALUES(`display_name`), `enabled` = VALUES(`enabled`);
INSERT INTO `applications` (`application_code`, `display_name`, `enabled`, `created_at`) VALUES ('wecall', 'WeCall', 1, '2026-08-06 02:17:48') ON DUPLICATE KEY UPDATE `application_code` = VALUES(`application_code`), `display_name` = VALUES(`display_name`), `enabled` = VALUES(`enabled`);
INSERT INTO `applications` (`application_code`, `display_name`, `enabled`, `created_at`) VALUES ('pmt', 'PMT for S&D', 1, '2026-08-06 02:17:48') ON DUPLICATE KEY UPDATE `application_code` = VALUES(`application_code`), `display_name` = VALUES(`display_name`), `enabled` = VALUES(`enabled`);
INSERT INTO `applications` (`application_code`, `display_name`, `enabled`, `created_at`) VALUES ('dspot', 'D.Spot', 1, '2026-08-06 02:17:48') ON DUPLICATE KEY UPDATE `application_code` = VALUES(`application_code`), `display_name` = VALUES(`display_name`), `enabled` = VALUES(`enabled`);
INSERT INTO `applications` (`application_code`, `display_name`, `enabled`, `created_at`) VALUES ('rared', 'RareD NovoCare', 1, '2026-08-06 02:17:48') ON DUPLICATE KEY UPDATE `application_code` = VALUES(`application_code`), `display_name` = VALUES(`display_name`), `enabled` = VALUES(`enabled`);
INSERT INTO `applications` (`application_code`, `display_name`, `enabled`, `created_at`) VALUES ('novocare_diabetes', 'NovoCare Diabetes', 1, '2026-08-06 02:17:48') ON DUPLICATE KEY UPDATE `application_code` = VALUES(`application_code`), `display_name` = VALUES(`display_name`), `enabled` = VALUES(`enabled`);
INSERT INTO `applications` (`application_code`, `display_name`, `enabled`, `created_at`) VALUES ('budget_tool', 'Budget Tool', 1, '2026-08-06 02:17:48') ON DUPLICATE KEY UPDATE `application_code` = VALUES(`application_code`), `display_name` = VALUES(`display_name`), `enabled` = VALUES(`enabled`);

-- application_aliases: 12 row(s)
INSERT INTO `application_aliases` (`alias`, `application_code`, `created_at`) VALUES ('iwe', 'iwe', '2026-08-06 02:17:48') ON DUPLICATE KEY UPDATE `alias` = VALUES(`alias`), `application_code` = VALUES(`application_code`);
INSERT INTO `application_aliases` (`alias`, `application_code`, `created_at`) VALUES ('wecall', 'wecall', '2026-08-06 02:17:48') ON DUPLICATE KEY UPDATE `alias` = VALUES(`alias`), `application_code` = VALUES(`application_code`);
INSERT INTO `application_aliases` (`alias`, `application_code`, `created_at`) VALUES ('pmt', 'pmt', '2026-08-06 02:17:48') ON DUPLICATE KEY UPDATE `alias` = VALUES(`alias`), `application_code` = VALUES(`application_code`);
INSERT INTO `application_aliases` (`alias`, `application_code`, `created_at`) VALUES ('PMT for S&D', 'pmt', '2026-08-06 02:17:48') ON DUPLICATE KEY UPDATE `alias` = VALUES(`alias`), `application_code` = VALUES(`application_code`);
INSERT INTO `application_aliases` (`alias`, `application_code`, `created_at`) VALUES ('dspot', 'dspot', '2026-08-06 02:17:48') ON DUPLICATE KEY UPDATE `alias` = VALUES(`alias`), `application_code` = VALUES(`application_code`);
INSERT INTO `application_aliases` (`alias`, `application_code`, `created_at`) VALUES ('D.Spot', 'dspot', '2026-08-06 02:17:48') ON DUPLICATE KEY UPDATE `alias` = VALUES(`alias`), `application_code` = VALUES(`application_code`);
INSERT INTO `application_aliases` (`alias`, `application_code`, `created_at`) VALUES ('rared', 'rared', '2026-08-06 02:17:48') ON DUPLICATE KEY UPDATE `alias` = VALUES(`alias`), `application_code` = VALUES(`application_code`);
INSERT INTO `application_aliases` (`alias`, `application_code`, `created_at`) VALUES ('RareD NovoCare', 'rared', '2026-08-06 02:17:48') ON DUPLICATE KEY UPDATE `alias` = VALUES(`alias`), `application_code` = VALUES(`application_code`);
INSERT INTO `application_aliases` (`alias`, `application_code`, `created_at`) VALUES ('novocare_diabetes', 'novocare_diabetes', '2026-08-06 02:17:48') ON DUPLICATE KEY UPDATE `alias` = VALUES(`alias`), `application_code` = VALUES(`application_code`);
INSERT INTO `application_aliases` (`alias`, `application_code`, `created_at`) VALUES ('NovoCare Diabetes', 'novocare_diabetes', '2026-08-06 02:17:48') ON DUPLICATE KEY UPDATE `alias` = VALUES(`alias`), `application_code` = VALUES(`application_code`);
INSERT INTO `application_aliases` (`alias`, `application_code`, `created_at`) VALUES ('budget_tool', 'budget_tool', '2026-08-06 02:17:48') ON DUPLICATE KEY UPDATE `alias` = VALUES(`alias`), `application_code` = VALUES(`application_code`);
INSERT INTO `application_aliases` (`alias`, `application_code`, `created_at`) VALUES ('Budget Tool', 'budget_tool', '2026-08-06 02:17:48') ON DUPLICATE KEY UPDATE `alias` = VALUES(`alias`), `application_code` = VALUES(`application_code`);

-- alert_rule_applications: 16 row(s)
INSERT INTO `alert_rule_applications` (`alert_name`, `application_code`, `created_at`) VALUES ('app_alert_iwe_Login_Failed', 'iwe', '2026-08-06 02:17:48') ON DUPLICATE KEY UPDATE `alert_name` = VALUES(`alert_name`), `application_code` = VALUES(`application_code`);
INSERT INTO `alert_rule_applications` (`alert_name`, `application_code`, `created_at`) VALUES ('app_alert_iwe_Data_Docking_Failure', 'iwe', '2026-08-06 02:17:48') ON DUPLICATE KEY UPDATE `alert_name` = VALUES(`alert_name`), `application_code` = VALUES(`application_code`);
INSERT INTO `alert_rule_applications` (`alert_name`, `application_code`, `created_at`) VALUES ('app_alert_wecall_Password_Verification_Failed', 'wecall', '2026-08-06 02:17:48') ON DUPLICATE KEY UPDATE `alert_name` = VALUES(`alert_name`), `application_code` = VALUES(`application_code`);
INSERT INTO `alert_rule_applications` (`alert_name`, `application_code`, `created_at`) VALUES ('app_alert_pmt_Dif_Light', 'pmt', '2026-08-06 02:17:48') ON DUPLICATE KEY UPDATE `alert_name` = VALUES(`alert_name`), `application_code` = VALUES(`application_code`);
INSERT INTO `alert_rule_applications` (`alert_name`, `application_code`, `created_at`) VALUES ('app_alert_pmt_Login_Failed', 'pmt', '2026-08-06 02:17:48') ON DUPLICATE KEY UPDATE `alert_name` = VALUES(`alert_name`), `application_code` = VALUES(`application_code`);
INSERT INTO `alert_rule_applications` (`alert_name`, `application_code`, `created_at`) VALUES ('app_alert_pmt_Token_Invalid', 'pmt', '2026-08-06 02:17:48') ON DUPLICATE KEY UPDATE `alert_name` = VALUES(`alert_name`), `application_code` = VALUES(`application_code`);
INSERT INTO `alert_rule_applications` (`alert_name`, `application_code`, `created_at`) VALUES ('app_alert_dspot_Login_Failed', 'dspot', '2026-08-06 02:17:48') ON DUPLICATE KEY UPDATE `alert_name` = VALUES(`alert_name`), `application_code` = VALUES(`application_code`);
INSERT INTO `alert_rule_applications` (`alert_name`, `application_code`, `created_at`) VALUES ('app_alert_dspot_Export_Failed', 'dspot', '2026-08-06 02:17:48') ON DUPLICATE KEY UPDATE `alert_name` = VALUES(`alert_name`), `application_code` = VALUES(`application_code`);
INSERT INTO `alert_rule_applications` (`alert_name`, `application_code`, `created_at`) VALUES ('app_alert_rared_Add_Role', 'rared', '2026-08-06 02:17:48') ON DUPLICATE KEY UPDATE `alert_name` = VALUES(`alert_name`), `application_code` = VALUES(`application_code`);
INSERT INTO `alert_rule_applications` (`alert_name`, `application_code`, `created_at`) VALUES ('app_alert_rared_Edit_Points', 'rared', '2026-08-06 02:17:48') ON DUPLICATE KEY UPDATE `alert_name` = VALUES(`alert_name`), `application_code` = VALUES(`application_code`);
INSERT INTO `alert_rule_applications` (`alert_name`, `application_code`, `created_at`) VALUES ('app_alert_rared_PII_export', 'rared', '2026-08-06 02:17:48') ON DUPLICATE KEY UPDATE `alert_name` = VALUES(`alert_name`), `application_code` = VALUES(`application_code`);
INSERT INTO `alert_rule_applications` (`alert_name`, `application_code`, `created_at`) VALUES ('app_alert_novocare_diabetes_Change_of_Role_Privileges', 'novocare_diabetes', '2026-08-06 02:17:48') ON DUPLICATE KEY UPDATE `alert_name` = VALUES(`alert_name`), `application_code` = VALUES(`application_code`);
INSERT INTO `alert_rule_applications` (`alert_name`, `application_code`, `created_at`) VALUES ('app_alert_novocare_diabetes_Modify_User', 'novocare_diabetes', '2026-08-06 02:17:48') ON DUPLICATE KEY UPDATE `alert_name` = VALUES(`alert_name`), `application_code` = VALUES(`application_code`);
INSERT INTO `alert_rule_applications` (`alert_name`, `application_code`, `created_at`) VALUES ('app_alert_novocare_diabetes_User_Data_Export', 'novocare_diabetes', '2026-08-06 02:17:48') ON DUPLICATE KEY UPDATE `alert_name` = VALUES(`alert_name`), `application_code` = VALUES(`application_code`);
INSERT INTO `alert_rule_applications` (`alert_name`, `application_code`, `created_at`) VALUES ('app_alert_budget_tool_Login_Failed', 'budget_tool', '2026-08-06 02:17:48') ON DUPLICATE KEY UPDATE `alert_name` = VALUES(`alert_name`), `application_code` = VALUES(`application_code`);
INSERT INTO `alert_rule_applications` (`alert_name`, `application_code`, `created_at`) VALUES ('app_alert_budget_tool_System_Error', 'budget_tool', '2026-08-06 02:17:48') ON DUPLICATE KEY UPDATE `alert_name` = VALUES(`alert_name`), `application_code` = VALUES(`application_code`);

-- user_roles: 6 row(s)
INSERT INTO `user_roles` (`username`, `role`, `enabled`, `created_at`, `updated_at`) VALUES ('admin', 'admin', 1, '2026-08-06 02:17:48', '2026-08-06 02:17:48') ON DUPLICATE KEY UPDATE `username` = VALUES(`username`), `role` = VALUES(`role`), `enabled` = VALUES(`enabled`), `updated_at` = VALUES(`updated_at`);
INSERT INTO `user_roles` (`username`, `role`, `enabled`, `created_at`, `updated_at`) VALUES ('adminboll', 'admin', 1, '2026-08-06 02:41:16', '2026-08-06 02:41:16') ON DUPLICATE KEY UPDATE `username` = VALUES(`username`), `role` = VALUES(`role`), `enabled` = VALUES(`enabled`), `updated_at` = VALUES(`updated_at`);
INSERT INTO `user_roles` (`username`, `role`, `enabled`, `created_at`, `updated_at`) VALUES ('adminsyil', 'admin', 1, '2026-08-06 02:41:16', '2026-08-06 02:41:16') ON DUPLICATE KEY UPDATE `username` = VALUES(`username`), `role` = VALUES(`role`), `enabled` = VALUES(`enabled`), `updated_at` = VALUES(`updated_at`);
INSERT INTO `user_roles` (`username`, `role`, `enabled`, `created_at`, `updated_at`) VALUES ('zhangsan', 'user', 1, '2026-08-06 02:41:16', '2026-08-06 02:41:16') ON DUPLICATE KEY UPDATE `username` = VALUES(`username`), `role` = VALUES(`role`), `enabled` = VALUES(`enabled`), `updated_at` = VALUES(`updated_at`);
INSERT INTO `user_roles` (`username`, `role`, `enabled`, `created_at`, `updated_at`) VALUES ('lisi', 'user', 1, '2026-08-06 02:41:16', '2026-08-06 02:41:16') ON DUPLICATE KEY UPDATE `username` = VALUES(`username`), `role` = VALUES(`role`), `enabled` = VALUES(`enabled`), `updated_at` = VALUES(`updated_at`);
INSERT INTO `user_roles` (`username`, `role`, `enabled`, `created_at`, `updated_at`) VALUES ('wangwu', 'user', 1, '2026-08-06 02:41:16', '2026-08-06 02:41:16') ON DUPLICATE KEY UPDATE `username` = VALUES(`username`), `role` = VALUES(`role`), `enabled` = VALUES(`enabled`), `updated_at` = VALUES(`updated_at`);

-- user_application_permissions: 3 row(s)
INSERT INTO `user_application_permissions` (`username`, `application_code`, `granted_by`, `created_at`) VALUES ('zhangsan', 'iwe', 'admin', '2026-08-06 02:41:16') ON DUPLICATE KEY UPDATE `username` = VALUES(`username`), `application_code` = VALUES(`application_code`), `granted_by` = VALUES(`granted_by`);
INSERT INTO `user_application_permissions` (`username`, `application_code`, `granted_by`, `created_at`) VALUES ('lisi', 'wecall', 'admin', '2026-08-06 02:41:16') ON DUPLICATE KEY UPDATE `username` = VALUES(`username`), `application_code` = VALUES(`application_code`), `granted_by` = VALUES(`granted_by`);
INSERT INTO `user_application_permissions` (`username`, `application_code`, `granted_by`, `created_at`) VALUES ('wangwu', 'pmt', 'admin', '2026-08-06 02:41:16') ON DUPLICATE KEY UPDATE `username` = VALUES(`username`), `application_code` = VALUES(`application_code`), `granted_by` = VALUES(`granted_by`);
