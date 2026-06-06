import asyncio
import time
from database.db import execute_query

async def check_escalations():
    """Background task to check for unresolved tickets and escalate them."""
    print("[Escalation Worker] Started background task for auto-escalations.")
    while True:
        try:
            # Sleep for 1 minute
            await asyncio.sleep(60)

            # 1. Fetch active tickets that are 'open' (meaning no action has been taken)
            tickets = execute_query(
                "SELECT e.id, e.ticket_id, e.assigned_to, e.last_notified_at, e.escalation_level, e.status, u.role as current_role "
                "FROM escalations e "
                "JOIN users u ON e.assigned_to = u.id "
                "WHERE e.status = 'open'",
                fetch="all"
            )

            if not tickets:
                continue

            # 2. Fetch escalation configs
            configs = execute_query("SELECT current_role, next_role, wait_time_minutes FROM mail_config WHERE is_active=1", fetch="all")
            config_map = {c["current_role"]: c for c in configs}

            for ticket in tickets:
                current_role = ticket["current_role"]
                
                # Check if this role has an escalation rule
                if current_role not in config_map:
                    continue
                
                rule = config_map[current_role]
                wait_time = rule["wait_time_minutes"] * 60  # convert to seconds
                
                # Calculate time elapsed since last notification or creation
                last_notified = ticket["last_notified_at"]
                
                import datetime
                if last_notified is None:
                    continue

                # Use UTC now to correctly calculate difference since DB stores naive UTC
                now_utc = datetime.datetime.now(datetime.UTC).replace(tzinfo=None)
                time_elapsed = (now_utc - last_notified).total_seconds()
                
                if time_elapsed >= wait_time:
                    next_role = rule["next_role"]
                    # Find a user with the next role to assign to (e.g. supervisor)
                    next_user = execute_query("SELECT id, email, name FROM users WHERE role = %s AND is_active = 1 LIMIT 1", (next_role,), fetch="one")
                    
                    if next_user:
                        subject = f"URGENT: Ticket {ticket['ticket_id']} Escalated!"
                        body_text = f"Dear {next_user['name']},\n\nTicket {ticket['ticket_id']} was not resolved by the {current_role} in time and has been escalated to you."
                        
                        print(f"🚨 [ESCALATION] Ticket {ticket['ticket_id']} breached {rule['wait_time_minutes']} min SLA for {current_role}.")
                        
                        from utils.email import send_email
                        send_email(next_user['email'], subject, body_text)
                        
                        # Update the ticket
                        new_level = ticket["escalation_level"] + 1
                        execute_query(
                            "UPDATE escalations SET assigned_to = %s, last_notified_at = CURRENT_TIMESTAMP, escalation_level = %s WHERE id = %s",
                            (next_user["id"], new_level, ticket["id"]),
                            fetch="none"
                        )
                        
                        # Insert a notification for the next user
                        execute_query(
                            "INSERT INTO notifications (user_id, title, message, type, status) VALUES (%s, %s, %s, %s, %s)",
                            (next_user["id"], "Ticket Escalated", f"Ticket {ticket['ticket_id']} has been escalated to you.", "escalation", "unread"),
                            fetch="none"
                        )

        except Exception as e:
            print(f"[Escalation Worker] Error: {e}")

