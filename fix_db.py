import os
import pymysql
from dotenv import load_dotenv
import sys

def fix_db():
    load_dotenv()
    try:
        conn = pymysql.connect(
            host=os.getenv("DB_HOST"),
            port=int(os.getenv("DB_PORT", 3306)),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD"),
            database=os.getenv("DB_NAME")
        )
        
        with conn.cursor() as cursor:
            # Check existing columns
            cursor.execute("DESCRIBE prompt_templates")
            columns = [row[0] for row in cursor.fetchall()]
            print("Existing columns in prompt_templates:", columns)
            
            if "template_text" not in columns:
                print("Adding missing column 'template_text'...")
                cursor.execute("ALTER TABLE prompt_templates ADD COLUMN template_text TEXT;")
                conn.commit()
                print("OK: Column 'template_text' added successfully!")
                
                # Check if we should insert the seed data for intent_classifier
                cursor.execute("SELECT COUNT(*) FROM prompt_templates WHERE agent_name = 'intent_classifier'")
                count = cursor.fetchone()[0]
                if count == 0:
                    print("Inserting seed data for 'intent_classifier'...")
                    cursor.execute("""
                        INSERT INTO prompt_templates (agent_name, template_text) VALUES 
                        ('intent_classifier', 'You are an intent classification agent. Analyze the user input and classify it into one of the following intents: policy_inquiry, policy_period, coverage_question, faq, renewal, address_update, phone_update, email_update, nominee_update, complaint, policy_cancellation, human_agent_request, document_request. Input: {user_input}')
                    """)
                    conn.commit()
                    print("OK: Seed data inserted!")
            else:
                print("Column 'template_text' already exists. Nothing to do.")
                
    except Exception as e:
        print(f"Error: {e}")
        
if __name__ == "__main__":
    # Fix for Windows console encoding
    if sys.stdout.encoding != 'utf-8':
        sys.stdout.reconfigure(encoding='utf-8')
    fix_db()
