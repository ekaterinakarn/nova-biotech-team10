// app.js — connects to the server, interpolates the hand at 60 fps, wires the controls.
//
// Responsibilities (kept OUT of hand.js so the hand renderer stays swappable):
//   - open the WebSocket, parse each Frame
//   - hold a `target` activation and ease `current` toward it every animation frame
//     (this is the "interpolate at 60 fps toward the last frame" from docs/02 — it's
//      why the hand looks smooth even though frames arrive at only 20 Hz)
//   - update the fidelity bar, state, coaching text, distances, signal light
//   - manual slider fallback (drive the hand with no server) and demo controls

import { createHand } from "./hand.js";

const WS_URL = "ws://127.0.0.1:8765";

const canvas = document.getElementById("hand");
const hand = createHand(canvas);

const el = (id) => document.getElementById(id);
const bar = el("fidelity-bar");
const stateLabel = el("state");
const coaching = el("coaching");
const distances = el("distances");
const conn = el("conn");
const slider = el("slider");
const manualToggle = el("manual");
const shamToggle = el("sham");

let target = 0;            // where the hand should go (from frame.activation or slider)
let current = 0;          // eased value actually rendered
let meta = { state: "rest", signalOk: true };
let manual = false;
let ws = null;

// ---- render loop: ease current -> target and draw, forever at ~60 fps ----
function tick() {
  current += (target - current) * 0.18;      // critically-damped-ish easing
  hand.applyPose(current, meta);
  requestAnimationFrame(tick);
}
requestAnimationFrame(tick);

// ---- WebSocket ----
function connect() {
  ws = new WebSocket(WS_URL);
  ws.onopen = () => { conn.textContent = "● connected"; conn.className = "ok"; };
  ws.onclose = () => {
    conn.textContent = "● disconnected — retrying"; conn.className = "bad";
    setTimeout(connect, 1500);               // auto-reconnect so a restart just works
  };
  ws.onmessage = (event) => {
    const f = JSON.parse(event.data);
    if (!manual) target = f.activation;
    meta = { state: f.state, signalOk: f.signal_ok };
    bar.style.width = `${(f.fidelity * 100).toFixed(0)}%`;
    bar.style.background = f.fidelity >= 0.6 ? "#39d98a"
      : f.fidelity <= 0.4 ? "#8a94a6" : "#f5c451";
    stateLabel.textContent = f.state.toUpperCase();
    coaching.textContent = f.coaching;
    distances.textContent = `d_exec ${f.d_exec}   d_rest ${f.d_rest}`;
    if (f.condition) el("condition").textContent = f.condition;
  };
}
connect();

// ---- manual slider fallback (works with no server at all) ----
manualToggle.addEventListener("change", () => {
  manual = manualToggle.checked;
  slider.disabled = !manual;
});
slider.addEventListener("input", () => {
  if (manual) { target = Number(slider.value) / 100; meta = { state: "engaged", signalOk: true }; }
});

// ---- sham toggle: tell the server to break / restore the model ----
shamToggle.addEventListener("change", () => {
  if (ws && ws.readyState === 1) ws.send(shamToggle.checked ? "sham:on" : "sham:off");
});

// ---- 5-condition demo buttons ----
document.querySelectorAll("[data-condition]").forEach((btn) => {
  btn.addEventListener("click", () => {
    const c = btn.getAttribute("data-condition");
    el("condition").textContent = c;
    if (ws && ws.readyState === 1) ws.send(`condition:${c}`);
  });
});
