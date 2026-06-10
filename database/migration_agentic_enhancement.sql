-- Database Migration Script for Agentic Backend Enhancement
-- This script safely adds new tables and indexes without altering existing ones.

CREATE TABLE IF NOT EXISTS `agent_configs` (
  `id` int NOT NULL AUTO_INCREMENT,
  `agent_name` varchar(100) NOT NULL,
  `model` varchar(100) DEFAULT 'gpt-4',
  `temperature` decimal(3,2) DEFAULT '0.00',
  `max_tokens` int DEFAULT '1000',
  `system_prompt_path` varchar(255) DEFAULT NULL,
  `is_active` tinyint(1) DEFAULT '1',
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `unique_agent_name` (`agent_name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `workflow_states` (
  `id` int NOT NULL AUTO_INCREMENT,
  `workflow_id` varchar(100) NOT NULL,
  `workflow_type` varchar(50) NOT NULL,
  `user_id` int NOT NULL,
  `current_step` varchar(100) NOT NULL,
  `status` varchar(50) DEFAULT 'pending',
  `context_data` json DEFAULT NULL,
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `unique_workflow_id` (`workflow_id`),
  KEY `idx_workflow_user` (`user_id`),
  CONSTRAINT `fk_workflow_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `agent_executions` (
  `id` int NOT NULL AUTO_INCREMENT,
  `agent_name` varchar(100) NOT NULL,
  `workflow_id` varchar(100) DEFAULT NULL,
  `user_id` int DEFAULT NULL,
  `input_data` json DEFAULT NULL,
  `output_data` json DEFAULT NULL,
  `status` varchar(50) DEFAULT 'success',
  `execution_time_ms` int DEFAULT NULL,
  `error_message` text,
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_agent_name` (`agent_name`),
  KEY `idx_agent_workflow` (`workflow_id`),
  KEY `idx_agent_user` (`user_id`),
  CONSTRAINT `fk_execution_workflow` FOREIGN KEY (`workflow_id`) REFERENCES `workflow_states` (`workflow_id`) ON DELETE SET NULL,
  CONSTRAINT `fk_execution_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Inserting default configuration for the agents
INSERT IGNORE INTO `agent_configs` (`agent_name`, `model`, `system_prompt_path`) VALUES
('supervisor_agent', 'gpt-4', 'prompts/intent/supervisor.txt'),
('intent_agent', 'gpt-4', 'prompts/intent/classifier.txt'),
('policy_agent', 'gpt-4', 'prompts/policy/handler.txt'),
('rag_agent', 'gpt-4', 'prompts/policy/rag.txt'),
('escalation_agent', 'gpt-4', 'prompts/escalation/handler.txt'),
('notification_agent', 'gpt-3.5-turbo', 'prompts/intent/notification.txt');
