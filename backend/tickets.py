import re

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


_STOP = {"the", "in", "is", "are", "not", "no", "number", "room", "a", "an", "of", "at",
         "near", "has", "have", "stopped", "working", "broken", "to", "and", "it", "my"}
_GENERIC = {"hostel", "lab", "hall", "block", "building", "floor"}


def _norm(loc):
    """'Room number 204', 'room-204' and 'Room 204' all become '204'."""
    s = (loc or "").lower()
    s = re.sub(r"\b(number|no|room|the)\b", " ", s)
    return re.sub(r"[^a-z0-9]", "", s)


def _tokens(*texts):
    words = re.findall(r"[a-z0-9]+", " ".join(t or "" for t in texts).lower())
    return {w for w in words if w not in _STOP and w not in _GENERIC}


def find_duplicate(category, location, issue=None):
    """Match an OPEN ticket: same normalized location, OR at least 2 shared
    meaningful words across location + issue (for example 'mess' and 'fan')."""
    key = _norm(location)
    if not key:
        return None
    mine = _tokens(location, issue)
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM tickets WHERE status = 'open' ORDER BY id DESC"
        ).fetchall()
    for r in rows:
        if _norm(r["location"]) == key:
            return r
        if len(mine & _tokens(r["location"], r["issue"])) >= 2:
            return r
    return None


def add_report(ticket_id, new_priority, new_reason):
    with get_conn() as conn:
        t = conn.execute("SELECT * FROM tickets WHERE id = %s", (ticket_id,)).fetchone()
        higher = PRIORITIES.index(new_priority) > PRIORITIES.index(t["priority"])
        priority = new_priority if higher else t["priority"]
        reason = new_reason if higher and new_reason else t["priority_reason"]
        return conn.execute(
            """UPDATE tickets SET report_count = report_count + 1,
               priority = %s, priority_reason = %s WHERE id = %s RETURNING *""",
            (priority, reason, ticket_id),
        ).fetchone()