import os
import pymysql
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_USER = os.getenv("DB_USER", "root")
DB_PASS = os.getenv("DB_PASS", "")
DB_NAME = os.getenv("DB_NAME", "insureai_db")

def truncate_transactional_tables():
    connection = None
    try:
        print(f"Connecting to MySQL database '{DB_NAME}' at {DB_HOST}...")
        connection = pymysql.connect(
            host=DB_HOST,
            user=DB_USER,
            password=DB_PASS,
            database=DB_NAME,
            cursorclass=pymysql.cursors.DictCursor
        )
        
        with connection.cursor() as cursor:
            print("Disabling foreign key checks...")
            cursor.execute("SET FOREIGN_KEY_CHECKS = 0;")
            
            tables_to_truncate = [
                "csr_notes",
                "guardrail_logs",
                "notifications",
                "uploaded_documents",
                "audit_logs",
                "escalations",
                "endorsements",
                "renewals",
                "chat_history",
                "policies"
            ]
            
            for table in tables_to_truncate:
                print(f"Truncating {table}...")
                cursor.execute(f"TRUNCATE TABLE {table};")
                
            print("Re-enabling foreign key checks...")
            cursor.execute("SET FOREIGN_KEY_CHECKS = 1;")
            
        connection.commit()
        print("\n✅ All transactional tables have been successfully truncated!")
        print("Note: The 'roles' and 'users' master tables were kept intact.")
        
    except Exception as e:
        print(f"\n❌ Error occurred while truncating tables: {e}")
        if connection:
            connection.rollback()
    finally:
        if connection:
            connection.close()

if __name__ == "__main__":
    confirm = input("\n⚠️ Are you sure you want to delete all transactional data? This cannot be undone. (y/n): ")
    if confirm.lower() == 'y':
        truncate_transactional_tables()
    else:
        print("Operation cancelled.")
