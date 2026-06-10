-- 003_constraints.sql

-- Adding foreign key constraints where applicable
-- Note: Assuming existing tables users, policies, etc. exist.

ALTER TABLE customer_preferences 
ADD CONSTRAINT fk_cust_pref_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;

ALTER TABLE session_memory 
ADD CONSTRAINT fk_session_memory_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;

ALTER TABLE episodic_memory 
ADD CONSTRAINT fk_episodic_memory_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;

ALTER TABLE policy_change_requests 
ADD CONSTRAINT fk_policy_change_req_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;

-- If policies table exists
-- ALTER TABLE policy_change_requests ADD CONSTRAINT fk_policy_change_req_policy FOREIGN KEY (policy_id) REFERENCES policies(id) ON DELETE CASCADE;

ALTER TABLE notification_queue 
ADD CONSTRAINT fk_notif_queue_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;

ALTER TABLE approval_history 
ADD CONSTRAINT fk_approval_hist_req FOREIGN KEY (approval_request_id) REFERENCES approval_requests(id) ON DELETE CASCADE;

ALTER TABLE sla_tracking 
ADD CONSTRAINT fk_sla_tracking_rule FOREIGN KEY (rule_id) REFERENCES sla_rules(id) ON DELETE CASCADE;
