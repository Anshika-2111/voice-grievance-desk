import json
import os
import re

import requests
from dotenv import load_dotenv

load_dotenv()

PRIORITIES = ("low", "medium", "high", "critical")

SYSTEM_PROMPT = """You are the brain of a campus Voice Grievance Desk (labs, hostel, library, classrooms).
The user's text comes from speech recognition, so expect small errors.
Decide ONE intent and reply with JSON only, exactly this shape:
{
  "intent": "create" | "list" | "resolve" | "unknown",
  "category": string|null,
  "location": string|null,
  "issue": string|null,
  "priority": "low"|"medium"|"high"|"critical"|null,
  "priority_reason": string|null,
  "time_constraint": string|null,
  "ticket_id": integer|null,
  "filters": {"status": "open"|"resolved"|null, "priority": string|null, "category": string|null, "location": string|null}
}
Rules:
- create: a person reports a problem. category is one of: maintenance, hostel, library, academic, it, safety, other. Use maintenance for AC, fans, lights, projectors, furniture, water, plumbing, electrical and equipment failures. Use it only for wifi, internet, computers and software. Fill location, a short issue, time_constraint if any deadline is mentioned (else null), priority and a short priority_reason that names the real factors (for example "Practical in 2 hours + equipment failure").
- Always write location in a short consistent form like "Room 204", "Lab 204", "Hostel B" (keep the type word and the number or letter, drop filler words such as "number"). Broken equipment in a room, lab or hall of an academic building is maintenance, never hostel unless the person says hostel.
- Priority: critical = danger to health or safety (fire, electric shock, gas leak, injury). high = blocks urgent work or has a near deadline. medium = real problem, no urgency. low = minor or cosmetic.
- list: an admin wants to see tickets. Put only what they asked for in filters. If they do not say resolved or all, use status "open".
- resolve: an admin wants to close a ticket. Set ticket_id as a plain integer (convert spoken numbers such as "ten forty two" to 1042).
- unknown: anything else or unclear.
- Fields that do not apply to the intent must be null (filters values too). Output JSON only, no markdown."""


class LLMBusy(Exception):
    """Rate limit hit (HTTP 429)."""


class LLMError(Exception):
    """Any other LLM failure."""


def _call_gemini(text):
    """The ONLY function that talks to the provider. Swap this to use Groq."""
    key = os.getenv("GEMINI_API_KEY")
    model = os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite")
    if not key:
        raise LLMError("GEMINI_API_KEY is missing in .env")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    body = {
        "systemInstruction": {"parts": [{"text": SYSTEM_PROMPT}]},
        "contents": [{"role": "user", "parts": [{"text": text}]}],
        "generationConfig": {"temperature": 0, "responseMimeType": "application/json"},
    }
    try:
        r = requests.post(url, json=body, headers={"x-goog-api-key": key}, timeout=20)
    except requests.RequestException:
        raise LLMError("Could not reach the AI service.")
    if r.status_code == 429:
        raise LLMBusy("The AI is busy right now. Please try again in a few seconds.")
    if r.status_code != 200:
        raise LLMError(f"AI service error {r.status_code}: {r.text[:200]}")
    try:
        parts = r.json()["candidates"][0]["content"]["parts"]
        return "".join(p.get("text", "") for p in parts if not p.get("thought"))
    except (KeyError, IndexError):
        raise LLMError("The AI returned an empty answer.")


def _extract_json(raw):
    raw = raw.strip()
    raw = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw)  # strip markdown fences
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        m = re.search(r"\{.*\}", raw, re.DOTALL)  # last resort: grab the {...} block
        if m:
            try:
                return json.loads(m.group(0))
            except json.JSONDecodeError:
                pass
    raise LLMError("The AI did not return valid JSON.")


def _clean(v):
    return v.strip() if isinstance(v, str) and v.strip() else None


def _validate(d):
    """Never trust LLM output: coerce everything into a safe, known shape."""
    if not isinstance(d, dict):
        raise LLMError("Unexpected AI answer.")
    intent = str(d.get("intent", "")).lower()
    if intent not in ("create", "list", "resolve"):
        return {"intent": "unknown"}
    out = {"intent": intent}
    if intent == "create":
        priority = str(d.get("priority") or "").lower()
        out.update(
            category=(_clean(d.get("category")) or "other").lower(),
            location=_clean(d.get("location")),
            issue=_clean(d.get("issue")),
            priority=priority if priority in PRIORITIES else "medium",
            priority_reason=_clean(d.get("priority_reason")),
            time_constraint=_clean(d.get("time_constraint")),
        )
        if not out["issue"]:
            return {"intent": "unknown"}
    elif intent == "list":
        f = d.get("filters") if isinstance(d.get("filters"), dict) else {}
        pr = str(f.get("priority") or "").lower()
        st = str(f.get("status") or "").lower()
        out["filters"] = {
            "priority": pr if pr in PRIORITIES else None,
            "status": st if st in ("open", "resolved") else None,
            "category": _clean(f.get("category")),
            "location": _clean(f.get("location")),
        }
    else:  # resolve
        try:
            out["ticket_id"] = int(d.get("ticket_id"))
        except (TypeError, ValueError):
            return {"intent": "unknown"}
    return out


def parse_command(text):
    return _validate(_extract_json(_call_gemini(text)))


if __name__ == "__main__":
    tests = [
        "The AC in Lab 204 has stopped working and our practical is in two hours",
        "There is a water leak near the hostel block B bathroom",
        "Show me all high priority complaints",
        "Mark ticket 1042 as resolved",
        "What is the weather today",
    ]
    for t in tests:
        print(t, "\n ->", json.dumps(parse_command(t)), "\n")