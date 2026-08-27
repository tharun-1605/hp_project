/**
 * Frontend WebSocket Telemetry Client & UI Controller for VisionNav
 */

let socket = null;
let synth = window.speechSynthesis;
let recognition = null;
let lastSpokenInstruction = "";

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

    if (synth && instr !== lastSpokenInstruction) {
      speakBrowserAudio(instr);
      lastSpokenInstruction = instr;
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
  el.innerText = `${label}: ${status}`;
  if (status === "BLOCKED") {
    el.style.borderColor = "var(--accent-red)";
    el.style.color = "var(--accent-red)";
  } else if (status === "PARTIALLY BLOCKED") {
    el.style.borderColor = "var(--accent-yellow)";
    el.style.color = "var(--accent-yellow)";
  } else {
    el.style.borderColor = "var(--accent-green)";
    el.style.color = "var(--accent-green)";
  }
}

function renderObjectsList(detections) {
  const listEl = document.getElementById("objectsList");
  document.getElementById("objCount").innerText = detections.length;

  if (!detections || detections.length === 0) {
    listEl.innerHTML = '<li class="empty-msg">No objects detected nearby.</li>';
    return;
  }

  listEl.innerHTML = detections.map(d => `
    <li>
      <span><strong>${d.class.toUpperCase()}</strong> (${d.zone || 'center'})</span>
      <span style="color: ${d.distance_m <= 1.0 ? 'var(--accent-red)' : 'var(--accent-yellow)'}">
        ${d.distance_m} meters
      </span>
    </li>
  `).join('');
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
