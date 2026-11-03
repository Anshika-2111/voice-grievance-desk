from db import get_conn

PRIORITIES = ("low", "medium", "high", "critical")


def create_ticket(category, location, issue, priority, priority_reason=None, time_constraint=None):
    with get_conn() as conn:
        return conn.execute(
            """INSERT INTO tickets (category, location, issue, priority, priority_reason, time_constraint)
               VALUES (%s, %s, %s, %s, %s, %s) RETURNING *""",
            (category, location, issue, priority, priority_reason, time_constraint),
        ).fetchone()


def list_tickets(priority=None, status=None, category=None, location=None):
    where, params = [], []
    if priority:
        where.append("priority = %s"); params.append(priority)
    if status:
        where.append("status = %s"); params.append(status)
    if category:
        where.append("category ILIKE %s"); params.append(category)
    if location:
        where.append("location ILIKE %s"); params.append(f"%{location}%")
    sql = "SELECT * FROM tickets"
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY id DESC"
    with get_conn() as conn:
        return conn.execute(sql, params).fetchall()


def resolve_ticket(ticket_id):
    with get_conn() as conn:
        return conn.execute(
            "UPDATE tickets SET status = 'resolved' WHERE id = %s RETURNING *",
            (ticket_id,),
        ).fetchone()  # None if the ticket doesn't exist