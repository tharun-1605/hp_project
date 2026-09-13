/**
 * Frontend WebSocket Telemetry Client & UI Controller for VisionNav
 */

let socket = null;
let synth = window.speechSynthesis;
let recognition = null;
let lastSpokenNormalized = "";
let lastSpokenTime = 0;

function connectWebSocket() {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  const wsUrl = `${protocol}//${window.location.host}/ws/telemetry`;

  console.log("Connecting WebSocket:", wsUrl);
  socket = new WebSocket(wsUrl);

  socket.onopen = () => {
    console.log("Connected to VisionNav real-time telemetry stream.");
    document.getElementById("videoPlaceholder").style.display = "none";
  };

  socket.onmessage = (event) => {
    const data = JSON.parse(event.data);
    updateDashboardUI(data);
  };

  socket.onclose = () => {
    console.warn("WebSocket connection lost. Reconnecting in 2 seconds...");
    setTimeout(connectWebSocket, 2000);
  };

  socket.onerror = (err) => {
    console.error("WebSocket error:", err);
  };
}

function updateDashboardUI(data) {
  // 1. Frame stream
  if (data.frame_b64) {
    const imgEl = document.getElementById("videoFeed");
    imgEl.src = "data:image/jpeg;base64," + data.frame_b64;
    document.getElementById("videoPlaceholder").style.display = "none";
  }

  // 2. Decision & Instruction
  if (data.decision) {
    const instr = data.decision.instruction || "System Ready";
    document.getElementById("activeInstruction").innerText = instr;

    const lowerInstr = instr.toLowerCase();
    const isIdleInstr = lowerInstr.includes("system ready") || lowerInstr.includes("no active");
    const normalized = instr.replace(/[\d.]+/g, "#").trim();
    const now = Date.now();

    // Auto-speak instructions ONLY if it's an active hazard/navigation guidance and not repeated within 5s
    if (synth && !isIdleInstr) {
      if (normalized !== lastSpokenNormalized || (now - lastSpokenTime) > 5000) {
        speakBrowserAudio(instr);
        lastSpokenNormalized = normalized;
        lastSpokenTime = now;
      }
    }
  }

  // 3. Risk Badge
  if (data.risk) {
    const rLevel = data.risk.level || "LOW";
    const badge = document.getElementById("riskBadge");
    badge.innerText = `RISK: ${rLevel}`;
    badge.className = `risk-badge risk-${rLevel.toLowerCase()}`;
  }

  // 4. Safe Path Corridors
  if (data.safe_path && data.safe_path.zones) {
    updateCorridorBox("corridorLeft", "LEFT", data.safe_path.zones.left);
    updateCorridorBox("corridorCenter", "CENTER", data.safe_path.zones.center);
    updateCorridorBox("corridorRight", "RIGHT", data.safe_path.zones.right);
  }

  // 5. GPS & Map
  if (data.gps) {
    const lat = data.gps.latitude;
    const lon = data.gps.longitude;
    document.getElementById("gpsCoord").innerText = `${lat.toFixed(4)}, ${lon.toFixed(4)}`;
    document.getElementById("gpsSpeed").innerText = `${data.gps.speed_mps} m/s`;

    if (typeof updateMapUserPosition === "function") {
      updateMapUserPosition(lat, lon, data.gps.bearing);
    }
  }

  // 6. Route Status
  if (data.route_status) {
    document.getElementById("navDist").innerText = `${data.route_status.distance_to_destination || 0} m`;
  }

  // 7. Detections List
  if (data.detections) {
    renderObjectsList(data.detections);
  }
}

function updateCorridorBox(elementId, label, status) {
  const el = document.getElementById(elementId);
  if (!el) return;
  const icon = label === "LEFT" ? "◄" : (label === "RIGHT" ? "►" : "▲");
  el.innerText = `${icon} ${label}: ${status}`;
  el.className = "corridor-box";
  if (status === "BLOCKED") {
    el.classList.add("corridor-blocked");
  } else if (status === "PARTIALLY BLOCKED") {
    el.classList.add("corridor-warning");
  }
}

function renderObjectsList(detections) {
  const listEl = document.getElementById("objectsList");
  document.getElementById("objCount").innerText = detections.length;

  if (!detections || detections.length === 0) {
    listEl.innerHTML = '<li class="empty-msg">No obstacles detected in visual field.</li>';
    return;
  }

  listEl.innerHTML = detections.map(d => {
    const distClass = d.distance_m <= 1.0 ? 'dist-close' : (d.distance_m <= 2.5 ? 'dist-medium' : 'dist-safe');
    const trackBadge = d.track_id ? `TRK-${d.track_id}` : '';
    const motionTag = d.motion_state && d.motion_state !== 'STATIONARY' ? ` • ${d.motion_state}` : '';
    return `
      <li class="object-card">
        <div class="obj-info">
          <span class="obj-class">${d.class} <small style="color: var(--cyan-neon); opacity: 0.8;">${trackBadge}</small></span>
          <span style="color: var(--text-muted); font-size: 0.78rem;">(${d.zone || 'center'}${motionTag})</span>
        </div>
        <span class="obj-distance ${distClass}">
          ${d.distance_m}m
        </span>
      </li>
    `;
  }).join('');
}

let selectedMaleVoice = null;

function loadMaleVoice() {
  if (!synth) return;
  const voices = synth.getVoices();
  selectedMaleVoice = voices.find(v => 
    v.lang.startsWith('en') && (
      v.name.toLowerCase().includes('male') ||
      v.name.toLowerCase().includes('david') ||
      v.name.toLowerCase().includes('george') ||
      v.name.toLowerCase().includes('mark') ||
      v.name.toLowerCase().includes('alex') ||
      v.name.toLowerCase().includes('daniel') ||
      v.name.toLowerCase().includes('guy')
    )
  ) || voices.find(v => v.lang.startsWith('en')) || voices[0];
}

if (window.speechSynthesis && window.speechSynthesis.onvoiceschanged !== undefined) {
  window.speechSynthesis.onvoiceschanged = loadMaleVoice;
}

function speakBrowserAudio(text) {
  if (!synth) return;
  synth.cancel(); // Interrupt previous speech for responsiveness
  const utterance = new SpeechSynthesisUtterance(text);
  utterance.rate = 1.0;
  if (!selectedMaleVoice) loadMaleVoice();
  if (selectedMaleVoice) {
    utterance.voice = selectedMaleVoice;
  }
  synth.speak(utterance);
}

function sendVoiceCommand(cmdText) {
  fetch('/api/voice/command', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ command: cmdText })
  })
  .then(res => res.json())
  .then(data => {
    console.log("Voice command response:", data);
    if (data.speak_text) {
      speakBrowserAudio(data.speak_text);
    }
    if (data.route && data.route.coordinates && typeof drawRoutePolyline === "function") {
      drawRoutePolyline(data.route.coordinates);
      document.getElementById("navDest").innerText = data.destination.name;
    }
  })
  .catch(err => console.error("Error sending voice command:", err));
}

function sendQuickCommand(text) {
  document.getElementById("commandInput").value = text;
  sendVoiceCommand(text);
}

function stopNav() {
  fetch('/api/navigation/stop', { method: 'POST' })
    .then(res => res.json())
    .then(() => {
      document.getElementById("navDest").innerText = "None";
    });
}

// Mode Selector Handler
document.getElementById("modeSelect").addEventListener("change", (e) => {
  const newMode = e.target.value;
  fetch('/api/mode', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ mode: newMode })
  });
});

// Command Form Handler
document.getElementById("commandForm").addEventListener("submit", (e) => {
  e.preventDefault();
  const input = document.getElementById("commandInput");
  if (input.value.trim()) {
    sendVoiceCommand(input.value.trim());
    input.value = "";
  }
});

// Microphone Web Speech API Setup
document.getElementById("btnMic").addEventListener("click", () => {
  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SpeechRecognition) {
    alert("Web Speech microphone recognition not supported in this browser. Type command instead.");
    return;
  }

  recognition = new SpeechRecognition();
  recognition.lang = 'en-US';
  recognition.start();

  const micBtn = document.getElementById("btnMic");
  micBtn.innerText = "🎙️ Listening...";
  micBtn.style.backgroundColor = "var(--accent-yellow)";
  micBtn.style.color = "#000";

  recognition.onresult = (event) => {
    const transcript = event.results[0][0].transcript;
    document.getElementById("commandInput").value = transcript;
    sendVoiceCommand(transcript);
  };

  recognition.onend = () => {
    micBtn.innerText = "🎤 MIC";
    micBtn.style.backgroundColor = "";
    micBtn.style.color = "";
  };
});

document.addEventListener("DOMContentLoaded", () => {
  connectWebSocket();
});
