import os
import sys
import uuid
import streamlit as st
import streamlit.components.v1 as components

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from dotenv import load_dotenv
from livekit import api

load_dotenv()

LIVEKIT_URL = os.getenv("LIVEKIT_URL", "wss://nepali-rag-agent-xlruksz0.livekit.cloud")
LIVEKIT_API_KEY = os.getenv("LIVEKIT_API_KEY", "")
LIVEKIT_API_SECRET = os.getenv("LIVEKIT_API_SECRET", "")

st.set_page_config(
    page_title="Nepali Voice AI Agent",
    page_icon="🎙️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

st.markdown("""
<style>
#MainMenu, footer, header { visibility: hidden; }
.block-container {
    padding: 0 !important;
    max-width: 100% !important;
}
iframe {
    border: none !important;
    width: 100vw !important;
    height: 100vh !important;
}
</style>
""", unsafe_allow_html=True)

room_name = "nepali-voice-room"
participant_id = f"user_{uuid.uuid4().hex[:6]}"

token = (
    api.AccessToken(LIVEKIT_API_KEY, LIVEKIT_API_SECRET)
    .with_identity(participant_id)
    .with_name(participant_id)
    .with_grants(api.VideoGrants(room_join=True, room=room_name))
    .to_jwt()
)

html_code = f"""
<!DOCTYPE html>
<html lang="ne">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1.0"/>
<title>Nepali Voice RAG Agent</title>
<script src="https://cdn.jsdelivr.net/npm/livekit-client@2.6.0/dist/livekit-client.umd.min.js"></script>
<link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;700&display=swap" rel="stylesheet">
<style>
* {{ box-sizing:border-box; margin:0; padding:0; font-family:'Outfit',sans-serif; }}
html,body {{ width:100vw; height:100vh; overflow:hidden; background:#030712; color:#f8fafc; }}

.app {{
    width:100vw; height:100vh;
    display:flex; flex-direction:column;
    align-items:center; justify-content:space-between;
    background:radial-gradient(circle at 50% 45%, #1e1b4b 0%, #0f172a 55%, #030712 100%);
    position:relative;
    padding-bottom:48px;
}}

/* Header */
.header {{ margin-top:28px; text-align:center; z-index:10; }}
.header h1 {{ font-size:24px; font-weight:700; letter-spacing:1px; }}
.header .subtitle {{ font-size:13px; color:#94a3b8; margin-top:6px; }}

#statusPill {{
    display:inline-block; margin-top:10px;
    padding:4px 16px; border-radius:999px; font-size:13px; font-weight:600;
    background:rgba(30,41,59,0.8); border:1px solid rgba(255,255,255,0.1);
    transition:all 0.4s ease;
}}
#statusPill.idle    {{ color:#94a3b8; border-color:#334155; }}
#statusPill.loading {{ color:#fbbf24; border-color:#f59e0b; box-shadow:0 0 12px rgba(245,158,11,0.4); }}
#statusPill.live    {{ color:#34d399; border-color:#10b981; box-shadow:0 0 14px rgba(16,185,129,0.5); }}

/* Center orb + canvas */
.stage {{
    position:absolute; top:47%; left:50%;
    transform:translate(-50%,-50%);
    width:340px; height:340px;
    display:flex; align-items:center; justify-content:center;
}}
#specCanvas {{
    position:absolute; top:0; left:0; width:340px; height:340px; z-index:1;
}}
.orb {{
    position:relative; z-index:5;
    width:180px; height:180px; border-radius:50%;
    background:linear-gradient(135deg,#0284c7,#0369a1);
    border:3px solid rgba(56,189,248,0.5);
    box-shadow:0 0 40px rgba(56,189,248,0.4), inset 0 0 20px rgba(255,255,255,0.1);
    display:flex; flex-direction:column; align-items:center; justify-content:center;
    cursor:pointer; user-select:none;
    transition:all 0.4s cubic-bezier(0.175,0.885,0.32,1.275);
}}
.orb:hover {{ transform:scale(1.06); }}
.orb-icon {{ font-size:40px; margin-bottom:6px; }}
.orb-label {{ font-size:13px; font-weight:700; letter-spacing:1.5px; text-transform:uppercase; }}

.orb.loading {{
    background:linear-gradient(135deg,#d97706,#92400e);
    border-color:#fbbf24;
    animation:pulseFade 1.2s infinite;
}}
.orb.live {{
    background:linear-gradient(135deg,#10b981,#047857);
    border-color:#34d399;
    box-shadow:0 0 50px rgba(16,185,129,0.6);
    animation:glowPulse 2.2s infinite;
}}

@keyframes pulseFade {{
    0%,100% {{ opacity:0.75; }}
    50% {{ opacity:1; }}
}}
@keyframes glowPulse {{
    0%,100% {{ box-shadow:0 0 35px rgba(16,185,129,0.45); }}
    50% {{ box-shadow:0 0 70px rgba(16,185,129,0.85); }}
}}

/* Transcript */
.transcript {{
    position:absolute; bottom:82px; width:90%; max-width:640px;
    max-height:120px; overflow-y:auto;
    background:rgba(15,23,42,0.7); backdrop-filter:blur(12px);
    border:1px solid rgba(255,255,255,0.08); border-radius:16px;
    padding:10px 16px; font-size:13px; z-index:10;
}}
.t-idle {{ color:#475569; font-style:italic; text-align:center; }}
.t-msg {{ margin-bottom:5px; line-height:1.5; }}
.t-user {{ color:#38bdf8; font-weight:600; }}
.t-agent {{ color:#34d399; font-weight:600; }}

/* Chat bar */
.chatbar {{
    width:100%; background:rgba(15,23,42,0.9); backdrop-filter:blur(16px);
    border-top:1px solid rgba(255,255,255,0.08);
    padding:13px 24px; display:flex; justify-content:center; z-index:20;
}}
.chatbar form {{ width:100%; max-width:680px; display:flex; gap:10px; }}
.chatbar input {{
    flex:1; background:rgba(30,41,59,0.8); border:1px solid rgba(255,255,255,0.12);
    border-radius:999px; padding:11px 20px; color:#f8fafc; font-size:14px; outline:none;
    transition:border-color 0.2s ease;
}}
.chatbar input:focus {{ border-color:#38bdf8; }}
.chatbar button {{
    background:linear-gradient(135deg,#0284c7,#0369a1);
    color:#fff; border:none; border-radius:999px; padding:11px 26px;
    font-weight:700; font-size:14px; cursor:pointer;
    box-shadow:0 4px 12px rgba(2,132,199,0.4); transition:transform 0.15s;
}}
.chatbar button:hover {{ transform:scale(1.04); }}
</style>
</head>
<body>
<div class="app">

  <div class="header">
    <h1>Nepali Voice RAG Agent</h1>
    <div class="subtitle">Real-time voice assistant</div>
    <div id="statusPill" class="idle">Click orb to start call</div>
  </div>

  <div class="stage">
    <canvas id="specCanvas" width="340" height="340"></canvas>
    <div id="orb" class="orb" onclick="toggleCall()">
      <div class="orb-icon" id="orbIcon">🎙️</div>
      <div class="orb-label" id="orbLabel">Start Call</div>
    </div>
  </div>

  <div class="transcript" id="transcript">
    <div class="t-idle">Session transcript will appear here...</div>
  </div>

  <div class="chatbar">
    <form onsubmit="sendMsg(event)">
      <input type="text" id="chatInput" placeholder="Type a message to the agent..." autocomplete="off"/>
      <button type="submit">Send</button>
    </form>
  </div>

</div>

<!-- Hidden audio container for remote agent audio -->
<div id="audioContainer" style="display:none;"></div>

<script>
const LIVEKIT_URL = "{LIVEKIT_URL}";
const TOKEN      = "{token}";

let room        = null;
let isActive    = false;
let audioCtx    = null;
let analyser    = null;
let dataArr     = null;
let rafId       = null;
let ringCtx     = null;
let ringTimeout = null;
let ringing     = false;

const orb        = document.getElementById('orb');
const orbIcon    = document.getElementById('orbIcon');
const orbLabel   = document.getElementById('orbLabel');
const pill       = document.getElementById('statusPill');
const transcript = document.getElementById('transcript');
const canvas     = document.getElementById('specCanvas');
const ctx2d      = canvas.getContext('2d');
const audioContainer = document.getElementById('audioContainer');

function setStatus(state, text) {{
    pill.className = state;
    pill.textContent = text;
}}

// ── Phone Ringing Synthesizer ──────────────────────────────────────────────
function startRing() {{
    if (ringing) return;
    ringing = true;
    ringCtx = new (window.AudioContext || window.webkitAudioContext)();

    function playRingCycle() {{
        if (!ringing) return;
        const now = ringCtx.currentTime;

        // Classic double-ring pattern: two 0.4s bursts separated by 0.2s gap
        for (let burst = 0; burst < 2; burst++) {{
            const t = now + burst * 0.6;

            // Tone A: 440 Hz
            const oscA = ringCtx.createOscillator();
            const gainA = ringCtx.createGain();
            oscA.type = 'sine';
            oscA.frequency.setValueAtTime(440, t);
            gainA.gain.setValueAtTime(0, t);
            gainA.gain.linearRampToValueAtTime(0.25, t + 0.02);
            gainA.gain.setValueAtTime(0.25, t + 0.38);
            gainA.gain.linearRampToValueAtTime(0, t + 0.4);
            oscA.connect(gainA);
            gainA.connect(ringCtx.destination);
            oscA.start(t);
            oscA.stop(t + 0.4);

            // Tone B: 480 Hz (layered for richer ring sound)
            const oscB = ringCtx.createOscillator();
            const gainB = ringCtx.createGain();
            oscB.type = 'sine';
            oscB.frequency.setValueAtTime(480, t);
            gainB.gain.setValueAtTime(0, t);
            gainB.gain.linearRampToValueAtTime(0.2, t + 0.02);
            gainB.gain.setValueAtTime(0.2, t + 0.38);
            gainB.gain.linearRampToValueAtTime(0, t + 0.4);
            oscB.connect(gainB);
            gainB.connect(ringCtx.destination);
            oscB.start(t);
            oscB.stop(t + 0.4);
        }}

        // Repeat every 3 seconds (0.4 + 0.2 + 0.4 burst + ~2s silence)
        ringTimeout = setTimeout(playRingCycle, 3000);
    }}

    playRingCycle();
}}

function stopRing() {{
    ringing = false;
    if (ringTimeout) {{ clearTimeout(ringTimeout); ringTimeout = null; }}
    if (ringCtx) {{ ringCtx.close().catch(() => {{}}); ringCtx = null; }}
}}
// ──────────────────────────────────────────────────────────────────────────

async function toggleCall() {{
    if (!isActive) await startCall();
    else endCall();
}}

async function startCall() {{
    try {{
        orb.className = 'orb loading';
        orbIcon.textContent = '🔔';
        orbLabel.textContent = 'Connecting';
        setStatus('loading', '🟡 Loading AI Agent & Connecting...');

        setTimeout(startRing, 200); // Start phone ringing 0.2s after click

        room = new LivekitClient.Room({{ adaptiveStream: true, dynacast: true }});

        room.on(LivekitClient.RoomEvent.ParticipantConnected, () => {{
            setStatus('loading', '🟡 Agent joined — initializing Agent...');
        }});

        // THE KEY: Every subscribed remote track → attach as audio element
        room.on(LivekitClient.RoomEvent.TrackSubscribed, (track, pub, participant) => {{
            if (track.kind !== LivekitClient.Track.Kind.Audio) return;

            // Attach track to <audio> element for playback
            const el = track.attach();
            el.id = 'agent-audio-' + Date.now();
            el.autoplay = true;
            el.volume = 1.0;
            audioContainer.appendChild(el);
            el.play().catch(e => console.warn('Audio play failed:', e));

            // Use raw MediaStream for analyser — independent of element playback state
            if (track.mediaStream) {{
                attachAnalyser(track.mediaStream);
            }}

            stopRing(); // Agent connected — stop ringing immediately
            orb.className = 'orb live';
            orbIcon.textContent = '📞';
            orbLabel.textContent = 'End Call';
            setStatus('live', '🟢 Connected — AI Voice Agent');
        }});

        room.on(LivekitClient.RoomEvent.TrackUnsubscribed, (track) => {{
            track.detach();
        }});

        room.on(LivekitClient.RoomEvent.DataReceived, (payload, participant) => {{
            addMsg(participant ? participant.identity : 'Agent', new TextDecoder().decode(payload));
        }});

        room.on(LivekitClient.RoomEvent.Disconnected, () => {{
            endCall();
        }});

        await room.connect(LIVEKIT_URL, TOKEN);
        await room.localParticipant.setMicrophoneEnabled(true);

        // If agent already in room when we join
        room.remoteParticipants.forEach(p => {{
            p.trackPublications.forEach(pub => {{
                if (pub.track && pub.kind === LivekitClient.Track.Kind.Audio) {{
                    const el = pub.track.attach();
                    el.autoplay = true; el.volume = 1.0;
                    audioContainer.appendChild(el);
                    el.play().catch(() => {{}});
                    if (pub.track.mediaStream) attachAnalyser(pub.track.mediaStream);
                    orb.className = 'orb live';
                    orbIcon.textContent = '📞';
                    orbLabel.textContent = 'End Call';
                    setStatus('live', '🟢 Connected — AI Voice Agent');
                }}
            }});
        }});

        isActive = true;
        startSpectrum();

    }} catch(err) {{
        console.error('Connection error:', err);
        setStatus('idle', '❌ Connection failed: ' + err.message);
        endCall();
    }}
}}

function endCall() {{
    stopRing();
    if (room) {{ room.disconnect(); room = null; }}
    if (rafId) {{ cancelAnimationFrame(rafId); rafId = null; }}
    // Remove all audio elements
    audioContainer.innerHTML = '';
    isActive = false;
    orb.className = 'orb';
    orbIcon.textContent = '🎙️';
    orbLabel.textContent = 'Start Call';
    setStatus('idle', 'Click orb to start call');
    ctx2d.clearRect(0, 0, canvas.width, canvas.height);
}}

function attachAnalyser(mediaStream) {{
    try {{
        if (!audioCtx || audioCtx.state === 'closed') {{
            audioCtx = new (window.AudioContext || window.webkitAudioContext)();
        }}
        if (audioCtx.state === 'suspended') audioCtx.resume();

        // Use createMediaStreamSource — works directly on the raw WebRTC audio stream
        // Audio plays through the <audio> element separately; this is analyser-only
        const src = audioCtx.createMediaStreamSource(mediaStream);
        analyser = audioCtx.createAnalyser();
        analyser.fftSize = 256;
        analyser.smoothingTimeConstant = 0.80;
        src.connect(analyser);
        // DO NOT connect to destination here — audio plays via the <audio> element
        dataArr = new Uint8Array(analyser.frequencyBinCount);
    }} catch(e) {{
        console.warn('Analyser setup:', e);
    }}
}}

function startSpectrum() {{
    const BARS   = 40;
    const cx     = canvas.width  / 2;
    const cy     = canvas.height / 2;
    const baseR  = 98;
    let   orbScale = 1.0;

    function render() {{
        ctx2d.clearRect(0, 0, canvas.width, canvas.height);

        let avgAmp = 0;
        if (analyser && dataArr) {{
            analyser.getByteFrequencyData(dataArr);
            // Compute average amplitude from lower half of spectrum (voice range)
            let sum = 0;
            const half = Math.floor(dataArr.length / 2);
            for (let k = 0; k < half; k++) sum += dataArr[k];
            avgAmp = sum / half / 255; // 0..1
        }}

        // Smoothly drive orb scale: 1.0 idle → up to 1.18 at full volume
        const targetScale = 1.0 + avgAmp * 0.18;
        orbScale += (targetScale - orbScale) * 0.18; // lerp
        if (isActive) {{
            orb.style.transform = `scale(${{orbScale.toFixed(3)}})`;  
        }}

        for (let i = 0; i < BARS; i++) {{
            const raw  = dataArr ? dataArr[Math.floor(i * dataArr.length / BARS)] : 0;
            let   len  = Math.max(8, (raw / 255) * 65);
            if (len < 12) len = 10 + Math.sin(Date.now() / 180 + i * 0.4) * 8; // idle breathe

            const angle = (i / BARS) * Math.PI * 2 - Math.PI / 2;
            const x1 = cx + Math.cos(angle) * baseR;
            const y1 = cy + Math.sin(angle) * baseR;
            const x2 = cx + Math.cos(angle) * (baseR + len);
            const y2 = cy + Math.sin(angle) * (baseR + len);

            const g = ctx2d.createLinearGradient(x1,y1,x2,y2);
            g.addColorStop(0,   '#0369a1');
            g.addColorStop(0.5, '#38bdf8');
            g.addColorStop(1,   '#34d399');

            ctx2d.strokeStyle = g;
            ctx2d.lineWidth   = 3.5;
            ctx2d.lineCap     = 'round';
            ctx2d.shadowBlur  = 10;
            ctx2d.shadowColor = '#38bdf8';
            ctx2d.beginPath();
            ctx2d.moveTo(x1,y1); ctx2d.lineTo(x2,y2);
            ctx2d.stroke();
        }}
        rafId = requestAnimationFrame(render);
    }}
    render();
}}

function addMsg(sender, text) {{
    // Clear idle placeholder on first message
    const idle = transcript.querySelector('.t-idle');
    if (idle) idle.remove();

    const d = document.createElement('div');
    d.className = 't-msg';
    const isUser = sender.toLowerCase().includes('user');
    d.innerHTML = `<span class="${{isUser ? 't-user' : 't-agent'}}">${{sender}}:</span> ${{text}}`;
    transcript.appendChild(d);
    transcript.scrollTop = transcript.scrollHeight;
}}

function sendMsg(e) {{
    e.preventDefault();
    const inp = document.getElementById('chatInput');
    const val = inp.value.trim();
    if (!val || !room) return;
    const data = new TextEncoder().encode(val);
    room.localParticipant.publishData(data, {{ reliable: true }});
    addMsg('You', val);
    inp.value = '';
}}
</script>
</body>
</html>
"""

components.html(html_code, height=730, scrolling=False)
