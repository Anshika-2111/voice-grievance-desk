# 🎙️ Voice Grievance Desk

> **Speak a campus complaint. AI understands it, creates a prioritised ticket, routes it, and talks back.**

A voice-first campus grievance desk built solo for the **Vocal Labs Voice AI Hackathon, Round 2** (3 November 2026, 6 hours).

## 🚀 Live Demo

| | |
|---|---|
| **Live application** | https://voice-grievance-desk.netlify.app |
| **Backend health check** | https://voice-grievance-api.onrender.com/api/health |
| **Source code** | https://github.com/Anshika-2111/voice-grievance-desk |

> **Demo notes:** The backend runs on Render's free tier and sleeps when idle, so the first request can take about 50 seconds. Use **Google Chrome**, because voice input relies on the browser Web Speech API.

## 💡 The Problem

Campus complaints about labs, hostels, the library and classrooms are scattered across WhatsApp groups, paper registers and word of mouth. As a result:

- Urgent issues get missed.
- Many students report the same problem separately.
- Nobody has one view of what is open.
- Students never know whether their complaint was recorded.
- Typing a detailed form is slower than just saying the problem.

**Voice Grievance Desk** lets a student simply speak, and the system does the rest.

## 🎯 How It Works

**Voice in → AI understands → Real action → Voice out**

```text
User speaks: "AC in Lab 204 has stopped working, practical in two hours"
        |
        v
Browser Web Speech API (speech -> text)
        |
        v
Flask API  --->  Gemini (intent + category + location + priority + reason, as strict JSON)
        |
        v
Backend validates the JSON, then acts on Neon Postgres
(create / attach duplicate / list / resolve)
        |
        v
Dashboard updates + reply sentence is spoken (SpeechSynthesis)
```

## ✨ Features

- 🎙️ **Voice-first:** speak naturally instead of filling a form.
- 🧠 **AI intent understanding:** Gemini extracts the intent (create, list, resolve), category, location, issue, priority and any time constraint.
- 🎫 **Automatic ticket creation:** a real ticket is stored in Postgres.
- 🚦 **Explainable priority:** every ticket shows a priority and the reason, for example "practical in two hours + equipment failure".
- 🔁 **Duplicate detection:** a repeat complaint is attached to the existing open ticket and its report count goes up, instead of creating a second ticket.
- 🔎 **Voice queries:** "Show me all high priority complaints."
- ✅ **Voice resolution:** "Mark ticket 1001 as resolved."
- 🧠 **"What the AI understood" card:** after each command the dashboard shows what Gemini extracted and the team it is routed to.
- ⏱️ **Simulated routing and due times:** each ticket shows an assigned team and a due time based on priority, with an overdue flag.
- 📊 **Live dashboard:** stat cards (open, high/critical, resolved, total reports) and a priority breakdown bar.
- ⌨️ **Text fallback:** the same pipeline works for typed commands if the mic or the room noise is a problem.

## 🧪 Example Commands

| Intent | Say |
|---|---|
| Create | "The fan in Hostel B mess is broken." |
| Create (urgent) | "The AC in Lab 204 has stopped working and our practical is in two hours." |
| Duplicate | "AC in Lab 204 is not working." |
| List | "Show me all high priority complaints." |
| Resolve | "Mark ticket 1001 as resolved." |

## 🏗️ Architecture

```text
Browser (React + Vite, Netlify)
   |  Web Speech API (STT)  /  SpeechSynthesis (TTS)
   |  HTTPS / REST
   v
Flask backend (Render)
   |  /api/command  /api/tickets  /api/health
   |
   +--->  Gemini (Google AI Studio free tier): intent + priority JSON
   |
   +--->  Neon Postgres: tickets table
```

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| Frontend | React + Vite |
| Speech to text | Browser Web Speech API (en-IN) |
| Text to speech | Browser SpeechSynthesis |
| Backend | Python, Flask, gunicorn |
| AI | Google Gemini (free tier) |
| Database | Neon Postgres (psycopg) |
| Hosting | Netlify (frontend), Render (backend) |

Everything runs on free tiers, with no billing and no card.

## 🗄️ Database

Table `tickets`:

| Column | Purpose |
|---|---|
| `id` | Ticket number (starts at 1001) |
| `category` | maintenance, hostel, library, academic, it, safety, other |
| `location` | Campus location, e.g. "Lab 204" |
| `issue` | Description of the problem |
| `priority` | low, medium, high or critical (CHECK constraint) |
| `priority_reason` | Why that priority was assigned |
| `time_constraint` | Deadline mentioned by the user, e.g. "practical in two hours" |
| `status` | open or resolved |
| `report_count` | Number of reports attached to the ticket |
| `created_at` | Creation timestamp |

## 🔌 API

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/api/health` | Health check |
| GET | `/api/tickets` | List tickets, with filters |
| POST | `/api/tickets` | Create a ticket |
| POST | `/api/tickets/<id>/resolve` | Resolve a ticket |
| POST | `/api/command` | Natural-language command: create, duplicate, list, resolve or unknown |

## 🔐 Reliability and Security Decisions

- **Secrets stay on the server.** The Gemini key and database URL live only in the backend environment. The frontend only knows the backend URL.
- **The model is never trusted blindly.** The backend strips Markdown fences, parses the JSON, and validates the intent and fields. Anything unclear becomes an `unknown` intent and no database action is taken.
- **One LLM integration point.** All Gemini calls go through `_call_gemini()` in `llm.py`, so the provider can be swapped by changing one function.
- **Rate limits are handled.** A Gemini 429 returns a friendly message instead of a crash.

## 📌 What Is Real vs Mocked

### ✅ Real
- Browser speech recognition (Web Speech API)
- Gemini intent parsing and priority reasoning
- Postgres storage on Neon
- Ticket creation, listing, filtering and resolution
- Duplicate detection
- Spoken replies (browser SpeechSynthesis)
- Live React dashboard, deployed frontend and backend

### ⚠️ Mocked or limited
- **Team routing and due times (SLA)** are computed in the frontend for display. No real message is sent to any team.
- **No login or roles.** Anyone can resolve any ticket.
- **No email or SMS notifications.**
- **English only.**
- **Duplicate matching is rule-based** (location and keywords on open tickets), not semantic, so differently worded complaints can be missed.
- **Chrome only** for the mic.
- **Render free tier cold start** and **Gemini free tier rate limits.**

## 💻 Run Locally

Prerequisites: Python 3, Node.js and npm, a Postgres database (for example a free Neon project), a Gemini API key, and Chrome.

```bash
git clone https://github.com/Anshika-2111/voice-grievance-desk.git
cd voice-grievance-desk
```

**Backend**

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
python app.py
```

Fill `backend/.env` with your own values for the variables listed below.

**Frontend** (in a second terminal)

```bash
cd frontend
npm install
npm run dev
```

Open the URL shown by Vite in Chrome.

## 🌐 Deployment and Environment Variables

Names only. Never commit real values.

| Where | Variables |
|---|---|
| Backend (Render, `backend/.env`) | `GEMINI_API_KEY`, `GEMINI_MODEL`, `DATABASE_URL`, `FRONTEND_ORIGIN` |
| Frontend (Netlify, `frontend/.env`) | `VITE_API_URL` |

Render: root directory `backend`, build `pip install -r requirements.txt`, start `gunicorn app:app`.
Netlify: base directory `frontend`, build `npm run build`, publish directory `frontend/dist`.

## 📁 Project Structure

```text
voice-grievance-desk/
├── backend/
│   ├── app.py            # Flask routes
│   ├── llm.py            # Gemini prompt, _call_gemini, JSON validation
│   ├── tickets.py        # create, list, resolve, duplicate detection
│   ├── db.py             # Postgres connection and schema
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   ├── src/
│   │   ├── App.jsx       # mic, dashboard, AI understood card
│   │   └── App.css
│   ├── package.json
│   └── ...
├── .gitignore
└── README.md
```

## 🎬 3-Minute Demo Flow

1. **Create:** "The AC in Lab 204 has stopped working and our practical is in two hours." Shows a HIGH ticket with its reason and routing.
2. **Create:** "The fan in Hostel B mess is broken." Shows a lower priority.
3. **Duplicate:** "AC in Lab 204 is not working." Attaches to ticket 1001, which now has 2 reports.
4. **Query:** "Show me all high priority complaints."
5. **Resolve:** "Mark ticket 1001 as resolved."
6. **Fallback:** the same command typed in the text box.

## 🔮 Future Improvements

- Authentication and role-based permissions
- Real email and SMS notifications to the routed team
- Hindi and other Indian languages
- Spoken follow-up questions when the location is missing
- Semantic duplicate detection
- Real team routing and SLA management

## 👩‍💻 Author

**Anshika**, final-year engineering student.
Built independently for the Vocal Labs Voice AI Hackathon, Round 2, on 3 November 2026.

> **Don't make students fill out another form. Let them speak.**