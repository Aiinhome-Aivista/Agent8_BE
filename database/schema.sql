-- InsureAI Pro - Complete Database Schema
-- Run: mysql -u root -p < schema.sql

CREATE DATABASE IF NOT EXISTS insureai_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE insureai_db;

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

-- 9. Notifications table
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


-- InsureAI Pro - Seed Data
USE insureai_db;

-- Seed roles master table first
INSERT INTO roles (name) VALUES 
('customer'), 
('csr'), 
('supervisor'), 
('compliance');

-- PASSWORD: 123456 (bcrypt hash: $2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMaHoT3aV1YaY3Ib9nGhGxD3Oy)
INSERT INTO users (name, email, phone, password, role, address) VALUES
('Sonia Khatun',    'customer@test.com',    '+91-98765-43210', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMaHoT3aV1YaY3Ib9nGhGxD3Oy', 'customer',   '42 MG Road, Bhubaneswar, Odisha 751001'),
('Himanshu Mahato', 'csr@test.com',         '+91-99887-76654', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMaHoT3aV1YaY3Ib9nGhGxD3Oy', 'csr',        NULL),
('Sanjib Sau',      'supervisor@test.com',  '+91-91234-56789', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMaHoT3aV1YaY3Ib9nGhGxD3Oy', 'supervisor', NULL),
('Suman Khamrai',   'compliance@test.com',  '+91-90000-11223', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMaHoT3aV1YaY3Ib9nGhGxD3Oy', 'compliance', NULL);
