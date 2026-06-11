import sys
import os
sys.path.append(os.path.abspath('d:/Agent-8/Agent8_BE'))
from database.db import execute_query

users = execute_query("SELECT id, name, email FROM users WHERE role='customer'", fetch="all")
print("Customers:")
for u in users:
    print(u)

policies = execute_query("SELECT id, customer_id, policy_number, policy_type FROM policies", fetch="all")
print("\nPolicies:")
for p in policies:
    print(p)
