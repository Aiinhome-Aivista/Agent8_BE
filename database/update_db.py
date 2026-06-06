import mysql.connector
import os
from dotenv import load_dotenv

load_dotenv()

conn = mysql.connector.connect(
    host=os.getenv('DB_HOST', 'localhost'),
    user=os.getenv('DB_USER', 'root'),
    password=os.getenv('DB_PASSWORD', ''),
    database=os.getenv('DB_NAME', 'insureai_db')
)

cursor = conn.cursor()

cursor.execute('''
CREATE TABLE IF NOT EXISTS mail_config (
    id INT AUTO_INCREMENT PRIMARY KEY,
    current_role VARCHAR(50) NOT NULL,
    next_role VARCHAR(50) NOT NULL,
    wait_time_minutes INT NOT NULL,
    is_active TINYINT(1) DEFAULT 1
)
''')

cursor.execute('TRUNCATE TABLE mail_config')
cursor.execute('''
INSERT INTO mail_config (current_role, next_role, wait_time_minutes) VALUES
('csr', 'supervisor', 5),
('supervisor', 'compliance', 5)
''')

try:
    cursor.execute('ALTER TABLE escalations ADD COLUMN last_notified_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP')
except Exception as e:
    print('last_notified_at may already exist:', e)

try:
    cursor.execute('ALTER TABLE escalations ADD COLUMN escalation_level INT DEFAULT 0')
except Exception as e:
    print('escalation_level may already exist:', e)

conn.commit()
print('Database updated successfully!')
