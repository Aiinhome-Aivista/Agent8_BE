# Enterprise Agentic AI Insurance Servicing Platform - V2 Architecture

This document serves as the complete source of truth for the Agent-8 backend (V2), detailing the databases, tables, and agent workflows.

---

## 1. Databases Used

The platform utilizes a dual-database approach to handle structured relational data and unstructured semantic data efficiently.

1. **MySQL (Primary Relational DB)**
   - **Database Name:** `insureai_db_v2`
   - **Purpose:** Stores users, policies, transactional data, agent execution logs, session memory, SLAs, and approvals.
   - **Connection:** Managed via `database/db.py` using `pymysql`.

2. **ChromaDB (Vector Database)**
   - **Purpose:** Stores document chunks and embeddings (`BAAI/bge-small-en-v1.5`) for semantic search.
   - **Usage:** Exclusively used by the **RAG Agent** to answer policy coverage and FAQ questions with citations.

---

## 2. Complete MySQL Tables (`insureai_db_v2`)

The new V2 schema consolidates all legacy and agentic features into the following tables:

### Core Insurance & CRM
- `roles`: System roles (customer, csr, supervisor, compliance).
- `users`: User profiles and authentication details.
- `policies`: Customer insurance policies (premium, coverage, expiry).
- `chat_history`: Complete record of user and AI interactions.
- `renewals`: Policy renewal transactions and payment status.
- `endorsements`: Policy updates (e.g., address, nominee changes).
- `escalations`: Support tickets routed to human CSRs.
- `audit_logs`: System-wide audit trail for compliance and security.
- `uploaded_documents`: User-uploaded files.
- `csr_notes`: Internal notes added by human agents on tickets.

### Agent Configuration & Workflows
- `agent_configs`: Active agents, models (GPT-4/GPT-3.5), and system prompt mappings.
- `workflow_states`: Active conversation workflows and current step tracking.
- `agent_executions`: Logs of every input/output processed by individual agents.
- `mail_config`: CSR routing timers for escalations.

### V2 Enterprise Agentic Tables (New)
- `otp_verifications`: Stores generated OTPs, expiration, and validation status for the Auth Agent.
- `session_memory`: Active short-term JSON context for ongoing conversations.
- `episodic_memory`: Long-term user preferences and past event summaries.
- `approval_requests`: Pending compliance approvals (e.g., policy cancellation).
- `approval_history`: Audit trail of actions taken by the Compliance Team.
- `sla_rules`: Defined SLA limits (e.g., 30 mins for High Priority Escalation).
- `sla_tracking`: Tracks active entity deadlines against SLA rules.
- `notification_templates`: Email/SMS templates with merge tags.
- `notification_queue`: Pending notifications managed by background workers.

---

## 3. Agents in the System

The platform operates on a **Supervisor-Worker Architecture**.

1. **Supervisor Agent:** The brain of the system. Enforces guardrails, maintains session memory, detects intents, and routes the query to the correct worker.
2. **Intent Agent:** Classifies user input into specific intents (e.g., `policy_inquiry`, `renewal`).
3. **Auth Agent:** Handles sensitive workflows by generating and verifying OTPs against the DB.
4. **Policy Agent:** Retrieves structured policy data (expiry, premium) from MySQL.
5. **RAG Agent:** Queries ChromaDB to answer complex coverage questions based on uploaded PDFs.
6. **Escalation Agent:** Creates support tickets in MySQL and assigns them to CSRs.
7. **Renewal Agent:** Validates payments and updates policy expiry dates.
8. **Approval & Compliance Agent:** Pauses workflows for sensitive requests (cancellation) and routes them to a human review queue.
9. **Notification Agent:** Queues emails/SMS templates for delivery.
10. **Guardrail Agent:** Ensures PII masking and blocks prompt injection attacks.

---

## 4. Current Codebase Status

- **Database:** Fully Ready. The `schema_v2.sql` file contains the exact structure described above.
- **Python Code (Backend):** Partially Ready. The routing logic, RAG, and basic agents work, but the newer V2 agents (`AuthAgent`, `ApprovalAgent`, `SLAAgent`, and `MemoryService`) currently contain placeholder logic. They need to be updated to write real SQL queries to the newly created tables.
