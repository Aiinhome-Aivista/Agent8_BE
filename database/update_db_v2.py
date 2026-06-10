import mysql.connector
import os
from dotenv import load_dotenv

load_dotenv()

# Connect to MySQL (without selecting a database initially to allow creation)
conn = mysql.connector.connect(
    host=os.getenv('DB_HOST', 'localhost'),
    user=os.getenv('DB_USER', 'root'),
    password=os.getenv('DB_PASSWORD', '')
)

cursor = conn.cursor()

print('Executing Complete V2 Schema (schema_v2.sql)...')
try:
    with open(os.path.join(os.path.dirname(__file__), 'schema_v2.sql'), 'r') as f:
        sql_script = f.read()
        # Split by semicolon and execute each statement
        for statement in sql_script.split(';'):
            if statement.strip():
                cursor.execute(statement)
    print('V2 database "insureai_db_v2" created and initialized successfully with all tables and seed data.')
except Exception as e:
    print('Error executing V2 architecture script:', e)

conn.commit()
conn.close()
print('Database setup complete. Make sure to update DB_NAME=insureai_db_v2 in your .env file!')
