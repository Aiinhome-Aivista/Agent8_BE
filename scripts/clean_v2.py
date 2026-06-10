import os
import shutil
import pymysql
from arango import ArangoClient
from dotenv import load_dotenv

# Load env
env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
load_dotenv(env_path)

print("Starting V2 Data Cleanup...")

# 1. Clear ChromaDB
chroma_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'chroma_store')
if os.path.exists(chroma_path):
    for filename in os.listdir(chroma_path):
        file_path = os.path.join(chroma_path, filename)
        try:
            if os.path.isfile(file_path) or os.path.islink(file_path):
                os.unlink(file_path)
            elif os.path.isdir(file_path):
                shutil.rmtree(file_path)
        except Exception as e:
            print(f'Failed to delete {file_path}. Reason: {e}')
    print("[OK] ChromaDB cleared.")

# 2. Clear Uploads
uploads_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'uploads')
if os.path.exists(uploads_path):
    for filename in os.listdir(uploads_path):
        file_path = os.path.join(uploads_path, filename)
        try:
            if os.path.isfile(file_path) or os.path.islink(file_path):
                os.unlink(file_path)
            elif os.path.isdir(file_path):
                shutil.rmtree(file_path)
        except Exception as e:
            print(f'Failed to delete {file_path}. Reason: {e}')
    print("[OK] Uploads folder cleared.")

# 3. Clear ArangoDB (Graph)
try:
    arango_host = os.getenv("ARANGO_HOST", "http://157.173.221.226:8529")
    arango_db = os.getenv("ARANGO_DB", "insureai_graph_v2")
    arango_user = os.getenv("ARANGO_USERNAME", "root")
    arango_pass = os.getenv("ARANGO_PASSWORD", "")
    
    client = ArangoClient(hosts=arango_host)
    sys_db = client.db("_system", username=arango_user, password=arango_pass)
    if sys_db.has_database(arango_db):
        sys_db.delete_database(arango_db)
        print(f"[OK] ArangoDB '{arango_db}' dropped. It will be auto-recreated on next run.")
    else:
        print(f"[INFO] ArangoDB '{arango_db}' does not exist, nothing to clean.")
except Exception as e:
    print(f"[ERROR] ArangoDB cleanup failed: {e}")

# 4. Clear MySQL Transactional Data
try:
    db_name = os.getenv("DB_NAME", "insureai_db_v2")
    conn = pymysql.connect(
        host=os.getenv("DB_HOST"),
        port=int(os.getenv("DB_PORT", 3306)),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        database=db_name
    )
    with conn.cursor() as cur:
        cur.execute("SET FOREIGN_KEY_CHECKS = 0;")
        tables = [
            "audit_logs", "chat_history", "csr_notes", 
            "endorsements", "escalations", "guardrail_logs", 
            "notifications", "renewals", "uploaded_documents",
            "session_memory", "episodic_memory", "approval_requests",
            "approval_history", "sla_tracking", "notification_queue",
            "otp_verifications", "policies"
        ]
        for t in tables:
            try:
                cur.execute(f"TRUNCATE TABLE {t};")
            except Exception as e:
                pass
        cur.execute("SET FOREIGN_KEY_CHECKS = 1;")
    conn.commit()
    conn.close()
    print(f"[OK] MySQL ({db_name}) transactional tables truncated. Users and Roles kept intact.")
except Exception as e:
    print(f"[ERROR] MySQL cleanup failed: {e}")

print("Cleanup complete!")
