import { useCallback, useEffect, useRef, useState } from "react";
import "./App.css";

const API = import.meta.env.VITE_API_URL || "http://localhost:5000";
const SR = window.SpeechRecognition || window.webkitSpeechRecognition;

function speak(text) {
  if (!("speechSynthesis" in window)) return;
  window.speechSynthesis.cancel();
  const u = new SpeechSynthesisUtterance(text);
  u.lang = "en-IN";
  window.speechSynthesis.speak(u);
}

export default function App() {
  const [tickets, setTickets] = useState([]);
  const [filter, setFilter] = useState(null);
  const [heard, setHeard] = useState("");
  const [reply, setReply] = useState("");
  const [typed, setTyped] = useState("");
  const [listening, setListening] = useState(false);
  const [busy, setBusy] = useState(false);
  const [stats, setStats] = useState({ open: 0, urgent: 0, resolved: 0, reports: 0 });
  const recRef = useRef(null);

  const loadAll = useCallback(async () => {
    try {
      const r = await fetch(`${API}/api/tickets`);
      const rows = await r.json();
      setTickets(rows);
      setStats({
        open: rows.filter((t) => t.status === "open").length,
        urgent: rows.filter((t) => t.status === "open" && ["high", "critical"].includes(t.priority)).length,
        resolved: rows.filter((t) => t.status === "resolved").length,
        reports: rows.reduce((n, t) => n + t.report_count, 0),
      });
    } catch {
      setReply("Cannot reach the server. It may be waking up, try again in a few seconds.");
    }
  }, []);

  useEffect(() => { loadAll(); }, [loadAll]);

  async function sendCommand(text) {
    if (!text.trim()) return;
    setHeard(text);
    setBusy(true);
    try {
      const r = await fetch(`${API}/api/command`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text }),
      });
      const data = await r.json();
      setReply(data.reply || "Something went wrong.");
      speak(data.reply || "Something went wrong.");
      if (data.intent === "list") {
        setTickets(data.tickets);
        setFilter(data.filters);
      } else {
        setFilter(null);
        await loadAll();
      }
    } catch {
      const m = "I cannot reach the server right now. Please try again.";
      setReply(m);
      speak(m);
    }
    setBusy(false);
  }

  function toggleMic() {
    if (!SR) { setReply("Speech recognition needs Chrome. Use the text box instead."); return; }
    if (listening) { recRef.current?.stop(); return; }
    const rec = new SR();
    rec.lang = "en-IN";
    rec.interimResults = false;
    rec.onstart = () => setListening(true);
    rec.onend = () => setListening(false);
    rec.onerror = (e) => setReply(`Mic problem (${e.error}). Please type your command instead.`);
    rec.onresult = (e) => sendCommand(e.results[0][0].transcript);
    recRef.current = rec;
    rec.start();
  }

  function submitTyped(e) {
    e.preventDefault();
    sendCommand(typed);
    setTyped("");
  }

  const chips = filter ? Object.entries(filter).filter(([, v]) => v).map(([k, v]) => `${k}: ${v}`) : [];

  return (
    <div className="app">
      <div className="hero">
        <h1>🎙️ Voice Grievance Desk</h1>
        <div className="sub">Speak a complaint. AI creates a prioritised ticket and talks back.</div>
      </div>

      <div className="stats">
        <div className="stat"><div className="num">{stats.open}</div><div className="lbl">Open tickets</div></div>
        <div className="stat urgent"><div className="num">{stats.urgent}</div><div className="lbl">High / critical open</div></div>
        <div className="stat done"><div className="num">{stats.resolved}</div><div className="lbl">Resolved</div></div>
        <div className="stat rep"><div className="num">{stats.reports}</div><div className="lbl">Total reports</div></div>
      </div>

      <div className="panel">
        <div className="row">
          <button className={`mic ${listening ? "on" : ""}`} onClick={toggleMic} disabled={busy}>
            {listening ? "■" : "🎤"}
          </button>
          <form className="row" style={{ flex: 1 }} onSubmit={submitTyped}>
            <input value={typed} onChange={(e) => setTyped(e.target.value)}
                   placeholder="Or type: The fan in Hostel B room 12 is broken" />
            <button className="send" disabled={busy}>Send</button>
          </form>
        </div>
        {listening && <div className="listening">🔴 Listening… speak now</div>}
        {heard && <div className="heard">You said: “{heard}”</div>}
        {reply && <div className="reply">🔊 {reply}</div>}
        <div className="hint">Try: “Show me all high priority complaints” · “Mark ticket 1001 as resolved”</div>
      </div>

      <div className="panel">
        <b>Tickets ({tickets.length})</b>
        {chips.length > 0 && (
          <>
            {chips.map((c) => <span key={c} className="chip">{c}</span>)}
            <span className="chip" onClick={() => { setFilter(null); loadAll(); }}>✕ clear</span>
          </>
        )}
        <table>
          <thead>
            <tr><th>#</th><th>Location</th><th>Issue</th><th>Priority &amp; why</th><th>Status</th><th>Created</th></tr>
          </thead>
          <tbody>
            {tickets.map((t) => (
              <tr key={t.id} className={`p-${t.priority} ${t.status === "resolved" ? "done" : ""}`}>
                <td>{t.id}{t.report_count > 1 && <div className="why">👥 {t.report_count} reports</div>}</td>
                <td>{t.location || "—"}<div className="why">{t.category}</div></td>
                <td>{t.issue}</td>
                <td><span className={`badge ${t.priority}`}>{t.priority}</span>
                  <div className="why">{t.priority_reason}</div></td>
                <td className={t.status}>{t.status}</td>
                <td className="why">{new Date(t.created_at).toLocaleString()}</td>
              </tr>
            ))}
            {tickets.length === 0 && <tr><td colSpan="6" className="why">No tickets yet. Say something!</td></tr>}
          </tbody>
        </table>
      </div>
    </div>
  );
}