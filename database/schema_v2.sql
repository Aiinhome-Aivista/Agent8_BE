-- InsureAI Pro V2 - Complete Agentic Database Schema
-- Run: mysql -u root -p < schema_v2.sql

CREATE DATABASE IF NOT EXISTS insureai_db_v2 CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE insureai_db_v2;

-- ==========================================
-- PART 1: CORE CRM & INSURANCE TABLES
-- ==========================================

-- 0. Roles master table
CREATE TABLE IF NOT EXISTS roles (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(50) UNIQUE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

-- 1. Users table (all roles)
CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(150) UNIQUE NOT NULL,
    phone VARCHAR(20),
    password VARCHAR(255) NOT NULL,
    role VARCHAR(50) NOT NULL,
    address TEXT,
    is_active TINYINT(1) DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (role) REFERENCES roles(name)
);

-- 2. Policies table
CREATE TABLE IF NOT EXISTS policies (
    id INT AUTO_INCREMENT PRIMARY KEY,
    policy_number VARCHAR(30) UNIQUE NOT NULL,
    customer_id INT NOT NULL,
    policy_type VARCHAR(50) NOT NULL,
    insurer VARCHAR(100) DEFAULT 'InsureAI General',
    premium DECIMAL(10,2) NOT NULL,
    coverage_amount DECIMAL(15,2) NOT NULL,
    start_date DATE NOT NULL,
    expiry_date DATE NOT NULL,
    status VARCHAR(20),
    policy_details JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (customer_id) REFERENCES users(id) ON DELETE CASCADE
);

-- 3. Chat history table
CREATE TABLE IF NOT EXISTS chat_history (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    session_id VARCHAR(100),
    user_message TEXT NOT NULL,
    ai_response TEXT NOT NULL,
    detected_intent VARCHAR(50),
    confidence_score DECIMAL(4,3),
    workflow_triggered VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- 4. Renewals table
CREATE TABLE IF NOT EXISTS renewals (
    id INT AUTO_INCREMENT PRIMARY KEY,
    policy_id INT NOT NULL,
    user_id INT NOT NULL,
    previous_expiry DATE,
    new_expiry DATE,
    amount DECIMAL(10,2) NOT NULL,
    payment_method VARCHAR(50),
    transaction_id VARCHAR(100),
    payment_status VARCHAR(20),
    renewed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (policy_id) REFERENCES policies(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- 5. Endorsements table
CREATE TABLE IF NOT EXISTS endorsements (
    id INT AUTO_INCREMENT PRIMARY KEY,
    policy_id INT NOT NULL,
    user_id INT NOT NULL,
    update_type VARCHAR(50) NOT NULL,
    old_value TEXT,
    new_value TEXT,
    status VARCHAR(20),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (policy_id) REFERENCES policies(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- 6. Escalations table
CREATE TABLE IF NOT EXISTS escalations (
    id INT AUTO_INCREMENT PRIMARY KEY,
    ticket_id VARCHAR(20) UNIQUE NOT NULL,
    user_id INT NOT NULL,
    policy_id INT,
    issue TEXT NOT NULL,
    category VARCHAR(50),
    priority VARCHAR(20),
    status VARCHAR(20),
    assigned_to INT,
    resolution_notes TEXT,
    last_notified_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    escalation_level INT DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (policy_id) REFERENCES policies(id) ON DELETE SET NULL,
    FOREIGN KEY (assigned_to) REFERENCES users(id) ON DELETE SET NULL
);

-- 7. Audit logs table
CREATE TABLE IF NOT EXISTS audit_logs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT,
    action VARCHAR(100) NOT NULL,
    entity_type VARCHAR(50),
    entity_id INT,
    details TEXT,
    ip_address VARCHAR(45),
    severity VARCHAR(20),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
);

-- 8. Uploaded documents table
CREATE TABLE IF NOT EXISTS uploaded_documents (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    policy_id INT,
    file_name VARCHAR(255) NOT NULL,
    file_path VARCHAR(500) NOT NULL,
    document_type VARCHAR(100),
    file_size INT,
    is_processed TINYINT(1) DEFAULT 0,
    uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (policy_id) REFERENCES policies(id) ON DELETE SET NULL
);

-- 9. Notifications table (Legacy)
CREATE TABLE IF NOT EXISTS notifications (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    title VARCHAR(200),
    message TEXT NOT NULL,
    type VARCHAR(30),
    status VARCHAR(20),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- 10. Guardrail logs table
CREATE TABLE IF NOT EXISTS guardrail_logs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT,
    session_id VARCHAR(100),
    violation_type VARCHAR(100) NOT NULL,
    message TEXT,
    severity VARCHAR(20),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
);

-- 11. CSR notes table
CREATE TABLE IF NOT EXISTS csr_notes (
    id INT AUTO_INCREMENT PRIMARY KEY,
    escalation_id INT NOT NULL,
    csr_id INT NOT NULL,
    note TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (escalation_id) REFERENCES escalations(id) ON DELETE CASCADE,
    FOREIGN KEY (csr_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Indexes for performance
CREATE INDEX idx_policies_customer ON policies(customer_id);
CREATE INDEX idx_chat_user ON chat_history(user_id);
CREATE INDEX idx_chat_session ON chat_history(session_id);
CREATE INDEX idx_escalations_user ON escalations(user_id);
CREATE INDEX idx_escalations_assigned ON escalations(assigned_to);
CREATE INDEX idx_audit_user ON audit_logs(user_id);
CREATE INDEX idx_audit_created ON audit_logs(created_at);
CREATE INDEX idx_notifications_user ON notifications(user_id, status);
CREATE INDEX idx_renewals_policy ON renewals(policy_id);


-- ==========================================
-- PART 2: AGENTIC WORKFLOW & CONFIG TABLES
-- ==========================================

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

CREATE TABLE IF NOT EXISTS mail_config (
    id INT AUTO_INCREMENT PRIMARY KEY,
    current_role VARCHAR(50) NOT NULL,
    next_role VARCHAR(50) NOT NULL,
    wait_time_minutes INT NOT NULL,
    is_active TINYINT(1) DEFAULT 1
);

-- ==========================================
-- PART 3: V2 ENTERPRISE EXTENSIONS 
-- ==========================================

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
    `request_type` VARCHAR(100) NOT NULL,
    `reference_id` INT NOT NULL,
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
    `entity_type` VARCHAR(50) NOT NULL,
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
    `status` VARCHAR(50) DEFAULT 'ACTIVE',
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (`rule_id`) REFERENCES `sla_rules`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 5. Notifications
CREATE TABLE IF NOT EXISTS `notification_templates` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `name` VARCHAR(100) NOT NULL,
    `channel` VARCHAR(50) NOT NULL,
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
    `status` VARCHAR(50) DEFAULT 'QUEUED',
    `retry_count` INT DEFAULT 0,
    `sent_at` TIMESTAMP NULL DEFAULT NULL,
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (`user_id`) REFERENCES `users`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ==========================================
-- PART 4: SEED DATA
-- ==========================================

INSERT INTO roles (name) VALUES 
('customer'), ('csr'), ('supervisor'), ('compliance');

-- PASSWORD: 123456
INSERT INTO users (name, email, phone, password, role, address) VALUES
('Sonia Khatun',    'customer@test.com',    '+91-98765-43210', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMaHoT3aV1YaY3Ib9nGhGxD3Oy', 'customer',   '42 MG Road, Bhubaneswar, Odisha 751001'),
('Himanshu Mahato', 'csr@test.com',         '+91-99887-76654', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMaHoT3aV1YaY3Ib9nGhGxD3Oy', 'csr',        NULL),
('Sanjib Sau',      'supervisor@test.com',  '+91-91234-56789', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMaHoT3aV1YaY3Ib9nGhGxD3Oy', 'supervisor', NULL),
('Suman Khamrai',   'compliance@test.com',  '+91-90000-11223', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMaHoT3aV1YaY3Ib9nGhGxD3Oy', 'compliance', NULL);

INSERT IGNORE INTO `agent_configs` (`agent_name`, `model`, `system_prompt_path`) VALUES
('supervisor_agent', 'gpt-4', 'prompts/intent/supervisor.txt'),
('intent_agent', 'gpt-4', 'prompts/intent/classifier.txt'),
('policy_agent', 'gpt-4', 'prompts/policy/handler.txt'),
('rag_agent', 'gpt-4', 'prompts/policy/rag.txt'),
('escalation_agent', 'gpt-4', 'prompts/escalation/handler.txt'),
('notification_agent', 'gpt-3.5-turbo', 'prompts/intent/notification.txt');

INSERT INTO mail_config (current_role, next_role, wait_time_minutes) VALUES
('csr', 'supervisor', 5),
('supervisor', 'compliance', 5);

INSERT IGNORE INTO `sla_rules` (`rule_name`, `entity_type`, `priority`, `max_duration_minutes`, `escalation_level`) VALUES
('High Priority Escalation', 'escalation', 'high', 30, 'supervisor'),
('Standard Approval Review', 'approval', 'normal', 120, 'compliance');

INSERT IGNORE INTO `notification_templates` (`name`, `channel`, `subject`, `body_template`) VALUES
('OTP Verification', 'email', 'Your Login OTP', 'Your OTP is {{otp}}. It expires in 5 minutes.'),
('Policy Renewal', 'email', 'Policy Renewal Confirmed', 'Dear {{name}}, your policy {{policy_number}} has been successfully renewed.');
