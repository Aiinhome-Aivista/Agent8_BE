-- V2 Agentic Architecture Schema Extensions (MySQL)
-- This script adds the missing tables for the Enterprise Agentic AI Insurance Servicing Platform
-- Note: Vector data (for RAG Agent) is stored in ChromaDB, not MySQL.

USE insureai_db;

-- 1. Auth Agent: OTP Verifications
CREATE TABLE IF NOT EXISTS `otp_verifications` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `user_id` INT NOT NULL,
    `otp_hash` VARCHAR(255) NOT NULL,
    `expires_at` TIMESTAMP NOT NULL,
    `is_verified` TINYINT(1) DEFAULT 0,
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (`user_id`) REFERENCES `users`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 2. Memory Service: Session & Episodic Memory
CREATE TABLE IF NOT EXISTS `session_memory` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `session_id` VARCHAR(100) NOT NULL,
    `user_id` INT NOT NULL,
    `context_data` JSON,
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY `idx_session` (`session_id`),
    FOREIGN KEY (`user_id`) REFERENCES `users`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `episodic_memory` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `user_id` INT NOT NULL,
    `event_type` VARCHAR(100) NOT NULL,
    `event_summary` TEXT,
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (`user_id`) REFERENCES `users`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 3. Approvals & Compliance
CREATE TABLE IF NOT EXISTS `approval_requests` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `request_type` VARCHAR(100) NOT NULL, -- e.g., 'coverage_increase', 'cancellation'
    `reference_id` INT NOT NULL, -- e.g., policy_id
    `requested_by` INT NOT NULL,
    `assigned_to` INT,
    `status` VARCHAR(50) DEFAULT 'PENDING',
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (`requested_by`) REFERENCES `users`(`id`) ON DELETE CASCADE,
    FOREIGN KEY (`assigned_to`) REFERENCES `users`(`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `approval_history` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `approval_request_id` INT NOT NULL,
    `action_taken` VARCHAR(50) NOT NULL,
    `action_by` INT NOT NULL,
    `comments` TEXT,
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (`approval_request_id`) REFERENCES `approval_requests`(`id`) ON DELETE CASCADE,
    FOREIGN KEY (`action_by`) REFERENCES `users`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 4. SLA Monitoring
CREATE TABLE IF NOT EXISTS `sla_rules` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `rule_name` VARCHAR(100) NOT NULL,
    `entity_type` VARCHAR(50) NOT NULL, -- e.g., 'escalation', 'approval'
    `priority` VARCHAR(50),
    `max_duration_minutes` INT NOT NULL,
    `escalation_level` VARCHAR(50),
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `sla_tracking` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `entity_type` VARCHAR(50) NOT NULL,
    `entity_id` INT NOT NULL,
    `rule_id` INT NOT NULL,
    `deadline` TIMESTAMP NOT NULL,
    `status` VARCHAR(50) DEFAULT 'ACTIVE', -- ACTIVE, MET, BREACHED
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (`rule_id`) REFERENCES `sla_rules`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 5. Notifications
CREATE TABLE IF NOT EXISTS `notification_templates` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `name` VARCHAR(100) NOT NULL,
    `channel` VARCHAR(50) NOT NULL, -- email, sms, in-app
    `subject` VARCHAR(255),
    `body_template` TEXT NOT NULL,
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `notification_queue` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `user_id` INT NOT NULL,
    `channel` VARCHAR(50) NOT NULL,
    `recipient` VARCHAR(255) NOT NULL,
    `subject` VARCHAR(255),
    `body` TEXT NOT NULL,
    `status` VARCHAR(50) DEFAULT 'QUEUED', -- QUEUED, SENT, FAILED
    `retry_count` INT DEFAULT 0,
    `sent_at` TIMESTAMP NULL DEFAULT NULL,
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (`user_id`) REFERENCES `users`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Insert Seed Data for SLA Rules & Notification Templates
INSERT IGNORE INTO `sla_rules` (`rule_name`, `entity_type`, `priority`, `max_duration_minutes`, `escalation_level`) VALUES
('High Priority Escalation', 'escalation', 'high', 30, 'supervisor'),
('Standard Approval Review', 'approval', 'normal', 120, 'compliance');

INSERT IGNORE INTO `notification_templates` (`name`, `channel`, `subject`, `body_template`) VALUES
('OTP Verification', 'email', 'Your Login OTP', 'Your OTP is {{otp}}. It expires in 5 minutes.'),
('Policy Renewal', 'email', 'Policy Renewal Confirmed', 'Dear {{name}}, your policy {{policy_number}} has been successfully renewed.');
