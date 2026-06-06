-- InsureAI Pro - Seed Data
USE insureai_db;

-- Clear existing data (order matters for FK constraints)
SET FOREIGN_KEY_CHECKS = 0;
TRUNCATE TABLE guardrail_logs;
TRUNCATE TABLE csr_notes;
TRUNCATE TABLE notifications;
TRUNCATE TABLE uploaded_documents;
TRUNCATE TABLE audit_logs;
TRUNCATE TABLE escalations;
TRUNCATE TABLE endorsements;
TRUNCATE TABLE renewals;
TRUNCATE TABLE chat_history;
TRUNCATE TABLE policies;
TRUNCATE TABLE users;
TRUNCATE TABLE roles;
SET FOREIGN_KEY_CHECKS = 1;

-- Seed roles master table first
INSERT INTO roles (name) VALUES 
('customer'), 
('csr'), 
('supervisor'), 
('compliance');

-- PASSWORD: 123456 (bcrypt hash: $2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMaHoT3aV1YaY3Ib9nGhGxD3Oy)
INSERT INTO users (name, email, phone, password, role, address) VALUES
('Customer',     'customer@test.com',    '+91-98765-43210', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMaHoT3aV1YaY3Ib9nGhGxD3Oy', 'customer',   '42 MG Road, Bhubaneswar, Odisha 751001'),
('CSR',          'csr@test.com',         '+91-99887-76654', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMaHoT3aV1YaY3Ib9nGhGxD3Oy', 'csr',        NULL),
('Supervisor',   'supervisor@test.com',  '+91-91234-56789', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMaHoT3aV1YaY3Ib9nGhGxD3Oy', 'supervisor', NULL),
('Compliance',   'compliance@test.com',  '+91-90000-11223', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMaHoT3aV1YaY3Ib9nGhGxD3Oy', 'compliance', NULL);

