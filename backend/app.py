import llm
import os
from dotenv import load_dotenv
from flask import Flask, jsonify, request
from flask_cors import CORS

import tickets
from db import init_db

load_dotenv()

app = Flask(__name__)
CORS(app, origins=[os.getenv("FRONTEND_ORIGIN", "http://localhost:5173")])
init_db()


@app.get("/api/health")
def health():
    return jsonify(status="ok")


@app.get("/api/tickets")
def get_tickets():
    rows = tickets.list_tickets(
        priority=request.args.get("priority"),
        status=request.args.get("status"),
        category=request.args.get("category"),
        location=request.args.get("location"),
    )
    return jsonify(rows)


@app.post("/api/tickets")
def post_ticket():
    d = request.get_json(silent=True) or {}
    if d.get("priority") not in tickets.PRIORITIES or not d.get("issue") or not d.get("category"):
        return jsonify(error="category, issue and a valid priority are required"), 400
    row = tickets.create_ticket(
        d["category"], d.get("location"), d["issue"], d["priority"],
        d.get("priority_reason"), d.get("time_constraint"),
    )
    return jsonify(row), 201


@app.post("/api/tickets/<int:ticket_id>/resolve")
def resolve(ticket_id):
    row = tickets.resolve_ticket(ticket_id)
    if not row:
        return jsonify(error=f"Ticket {ticket_id} not found"), 404
    return jsonify(row)

def speak_list(rows, f):
    if not rows:
        return "I found no matching tickets."
    label = " ".join(x for x in [f.get("status"), f.get("priority") and f"{f['priority']}-priority"] if x)
    top = rows[0]
    where = f" in {top['location']}" if top["location"] else ""
    return (f"There are {len(rows)} {label} tickets. "
            f"The latest is ticket {top['id']}{where}: {top['issue']}.")


@app.post("/api/command")
def command():
    text = ((request.get_json(silent=True) or {}).get("text") or "").strip()
    if not text:
        return jsonify(error="No text received", reply="I didn't hear anything. Please try again."), 400
    try:
        cmd = llm.parse_command(text)
    except llm.LLMBusy as e:
        return jsonify(error="busy", reply=str(e)), 429
    except llm.LLMError as e:
        print("LLM error:", e)
        return jsonify(error="llm", reply="Sorry, I had trouble understanding that. Please try again."), 502

    intent = cmd["intent"]
    if intent == "create":
        t = tickets.create_ticket(cmd["category"], cmd["location"], cmd["issue"],
                                  cmd["priority"], cmd["priority_reason"], cmd["time_constraint"])
        where = f" for {t['location']}" if t["location"] else ""
        reply = (f"Registered as a {t['priority']}-priority {t['category']} ticket{where}. "
                 f"Ticket number {t['id']}.")
        return jsonify(intent=intent, reply=reply, ticket=t)
    if intent == "list":
        f = cmd["filters"]
        rows = tickets.list_tickets(**f)
        return jsonify(intent=intent, reply=speak_list(rows, f), filters=f, tickets=rows)
    if intent == "resolve":
        t = tickets.resolve_ticket(cmd["ticket_id"])
        if not t:
            return jsonify(intent=intent, reply=f"I couldn't find ticket {cmd['ticket_id']}.")
        return jsonify(intent=intent, reply=f"Ticket {t['id']} is marked as resolved.", ticket=t)
    return jsonify(intent="unknown",
                   reply="Sorry, I didn't catch that. You can report a problem, ask to show tickets, or resolve a ticket.")


if __name__ == "__main__":
    app.run(debug=True, port=5000)