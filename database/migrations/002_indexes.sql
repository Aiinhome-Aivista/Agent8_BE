-- 002_indexes.sql

-- RAG
CREATE INDEX IF NOT EXISTS idx_doc_chunks_doc_id ON document_chunks(document_id);
CREATE INDEX IF NOT EXISTS idx_doc_embeddings_chunk_id ON document_embeddings(chunk_id);

-- Memory
CREATE INDEX IF NOT EXISTS idx_cust_pref_user_id ON customer_preferences(user_id);
CREATE INDEX IF NOT EXISTS idx_session_memory_user_id ON session_memory(user_id);
CREATE INDEX IF NOT EXISTS idx_session_memory_session_id ON session_memory(session_id);
CREATE INDEX IF NOT EXISTS idx_episodic_memory_user_id ON episodic_memory(user_id);

-- Transactions
CREATE INDEX IF NOT EXISTS idx_policy_change_req_policy_id ON policy_change_requests(policy_id);
CREATE INDEX IF NOT EXISTS idx_policy_change_req_user_id ON policy_change_requests(user_id);

-- Approvals
CREATE INDEX IF NOT EXISTS idx_approval_req_ref_id ON approval_requests(reference_id);
CREATE INDEX IF NOT EXISTS idx_approval_hist_req_id ON approval_history(approval_request_id);

-- Documents
CREATE INDEX IF NOT EXISTS idx_gen_docs_ref_id ON generated_documents(reference_id);

-- Notifications
CREATE INDEX IF NOT EXISTS idx_notif_queue_user_id ON notification_queue(user_id);
CREATE INDEX IF NOT EXISTS idx_notif_queue_status ON notification_queue(status);

-- Configuration
CREATE INDEX IF NOT EXISTS idx_prompt_templates_agent ON prompt_templates(agent_name);
CREATE INDEX IF NOT EXISTS idx_tool_registry_name ON tool_registry(tool_name);
CREATE INDEX IF NOT EXISTS idx_workflow_config_name ON workflow_configurations(workflow_name);

-- SLA
CREATE INDEX IF NOT EXISTS idx_sla_tracking_entity ON sla_tracking(entity_type, entity_id);
CREATE INDEX IF NOT EXISTS idx_sla_tracking_status ON sla_tracking(status);

-- Monitoring
CREATE INDEX IF NOT EXISTS idx_agent_metrics_agent ON agent_metrics(agent_name);
CREATE INDEX IF NOT EXISTS idx_sys_health_logs_comp ON system_health_logs(component_name);
