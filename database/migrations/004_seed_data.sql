-- 004_seed_data.sql

-- SLA Rules
INSERT INTO sla_rules (rule_name, entity_type, priority, max_duration_minutes, escalation_level) VALUES
('CSR Standard SLA', 'ticket', 'HIGH', 5, 'Supervisor'),
('Supervisor Escalation SLA', 'ticket', 'HIGH', 10, 'Manager'),
('Compliance Review SLA', 'approval', 'CRITICAL', 15, 'Director');

-- Tool Registry
INSERT INTO tool_registry (tool_name, description, parameters_schema) VALUES
('get_policy_details', 'Retrieve details for a specific policy using policy number.', '{"type": "object", "properties": {"policy_number": {"type": "string"}}, "required": ["policy_number"]}'),
('get_customer_profile', 'Fetch customer profile information.', '{"type": "object", "properties": {"user_id": {"type": "integer"}}, "required": ["user_id"]}'),
('search_documents', 'Perform semantic search on policy documents.', '{"type": "object", "properties": {"query": {"type": "string"}, "top_k": {"type": "integer", "default": 5}}, "required": ["query"]}'),
('create_ticket', 'Create a support ticket for escalation.', '{"type": "object", "properties": {"user_id": {"type": "integer"}, "issue_summary": {"type": "string"}}, "required": ["user_id", "issue_summary"]}'),
('generate_pdf', 'Generate a PDF document.', '{"type": "object", "properties": {"document_type": {"type": "string"}, "reference_id": {"type": "integer"}}, "required": ["document_type", "reference_id"]}'),
('send_email', 'Send an email notification.', '{"type": "object", "properties": {"recipient": {"type": "string"}, "subject": {"type": "string"}, "body": {"type": "string"}}, "required": ["recipient", "subject", "body"]}'),
('send_sms', 'Send an SMS notification.', '{"type": "object", "properties": {"recipient_phone": {"type": "string"}, "message": {"type": "string"}}, "required": ["recipient_phone", "message"]}'),
('send_whatsapp', 'Send a WhatsApp notification.', '{"type": "object", "properties": {"recipient_phone": {"type": "string"}, "message": {"type": "string"}}, "required": ["recipient_phone", "message"]}'),
('log_audit', 'Log an audit event.', '{"type": "object", "properties": {"event_type": {"type": "string"}, "details": {"type": "string"}}, "required": ["event_type", "details"]}');

-- Prompt Templates
INSERT INTO prompt_templates (agent_name, template_text) VALUES
('intent_classifier', 'You are an intent classification agent. Analyze the user input and classify it into one of the following intents: policy_inquiry, policy_period, coverage_question, faq, renewal, address_update, phone_update, email_update, nominee_update, complaint, policy_cancellation, human_agent_request, document_request. Input: {user_input}'),
('policy_agent', 'You are a Policy Agent. You have access to the user''s policy details. Answer their queries regarding policy number, policy period, and coverage. Context: {policy_context} Query: {user_query}'),
('rag_agent', 'You are a RAG Agent. Answer the user''s question strictly based on the provided document context. If the answer is not in the context, say "I do not have that information." Context: {document_context} Query: {user_query}'),
('renewal_agent', 'You are a Renewal Agent. Guide the user through the policy renewal process, validate payment, and confirm renewal. User Context: {user_context}'),
('escalation_summary', 'Summarize the following conversation and intent for escalation to a human agent. Conversation: {chat_history} Intent: {detected_intent}'),
('notification_agent', 'You are a Notification Agent. Format the notification message for the selected channel ({channel}). Message context: {message_context}');
