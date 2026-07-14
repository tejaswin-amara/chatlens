
let currentChat = null;
let hourChart = null;
let dayChart = null;

async function fetchJSON(url, opts) {
  const r = await fetch(url, opts);
  return r.json();
}

function esc(s) { const d = document.createElement('div'); d.textContent = s; return d.innerHTML; }

function formatAI(text) {
  return text
    .replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;')
    .replace(/\\\\\\\\\*\\\\\\\\\*(.+?)\\\\\\\\\*\\\\\\\\\*/g, '<strong style="color:var(--text-primary)">$1</strong>')
    .replace(/\\\\\\\\\*(.+?)\\\\\\\\\*/g, '<em>$1</em>')
    .replace(/^### (.+)$/gm, '<h3 style="color:var(--accent-teal);margin-top:10px;margin-bottom:5px">$1</h3>')
    .replace(/^## (.+)$/gm, '<h2 style="color:var(--text-primary);margin-top:10px;margin-bottom:5px">$1</h2>')
    .replace(/^# (.+)$/gm, '<h1 style="color:var(--text-primary);margin-top:10px;margin-bottom:5px">$1</h1>')
    .replace(/^[-*] (.+)$/gm, '<li>$1</li>')
    .replace(/\\\\\\\\\n/g, '<br>');
}

// Responsive Sidebar toggling
function toggleSidebar(side) {
    if (side === 'left') {
        const active = document.getElementById('leftSidebar').classList.toggle('open');
        if (active) {
            document.getElementById('rightSidebar').classList.remove('open');
            document.getElementById('sidebarOverlay').classList.add('open');
        } else {
            document.getElementById('sidebarOverlay').classList.remove('open');
        }
    } else if (side === 'right') {
        const active = document.getElementById('rightSidebar').classList.toggle('open');
        if (active) {
            document.getElementById('leftSidebar').classList.remove('open');
            document.getElementById('sidebarOverlay').classList.add('open');
        } else {
            document.getElementById('sidebarOverlay').classList.remove('open');
        }
    }
}

function closeAllSidebars() {
    document.getElementById('leftSidebar').classList.remove('open');
    document.getElementById('rightSidebar').classList.remove('open');
    document.getElementById('sidebarOverlay').classList.remove('open');
}

async function loadChats() {
  const chats = await fetchJSON('/api/chats');
  const el = document.getElementById('chatList');
  if (!chats.length) { el.innerHTML = '<div class="empty-state">No chats imported yet.</div>'; return; }
  el.innerHTML = chats.map(c => `
    <div class="sim-chat-item" data-name="${esc(c.name)}" onclick="selectChat('${esc(c.name)}')">
      <div class="sim-chat-info">
        <div class="sim-chat-name">${esc(c.name)}</div>
        <div class="sim-chat-meta">
            <span class="sim-platform-tag sim-platform-${c.platform.toLowerCase()}">${c.platform}</span>
            <span>${c.message_count.toLocaleString()} msgs</span>
        </div>
      </div>
    </div>
  `).join('');

  const stats = await fetchJSON('/api/stats');
  document.getElementById('statsLine').textContent = `${stats.total_messages.toLocaleString()} messages · ${stats.total_chats} chats`;
}

async function selectChat(name) {
  currentChat = name;
  document.querySelectorAll('.sim-chat-item').forEach(el => el.classList.toggle('active', el.dataset.name === name));
  document.getElementById('welcome').style.display = 'none';
  document.getElementById('topbar').style.display = 'flex';
  document.getElementById('rightSidebar').style.display = 'flex';
  document.getElementById('toggleRightBtn').style.display = 'block';
  document.getElementById('topbarTitle').textContent = name;
  
  document.getElementById('ai-output-text').innerHTML = "Select a preset check below or write a custom query to trigger Gemini's context parsing.";
  
  closeAllSidebars();
  switchView('messages');
}

function switchView(view) {
  document.getElementById('messages').style.display = view === 'messages' ? 'flex' : 'none';
  document.getElementById('dashboard').style.display = view === 'dashboard' ? 'flex' : 'none';
  
  const tabs = document.querySelectorAll('#viewTabs .sim-tab-btn');
  tabs[0].classList.toggle('active', view === 'messages');
  tabs[1].classList.toggle('active', view === 'dashboard');

  if (view === 'messages') loadMessages();
  if (view === 'dashboard') loadDashboard();
}

async function loadMessages() {
  const msgEl = document.getElementById('messages');
  msgEl.innerHTML = '<div class="empty-state"><span class="spinner"></span> Loading messages...</div>';
  const msgs = await fetchJSON(`/api/messages?chat=${encodeURIComponent(currentChat)}&limit=200`);
  
  if (!msgs.length) { msgEl.innerHTML = '<div class="empty-state">No messages.</div>'; return; }

  const senders = [...new Set(msgs.map(m => m.sender))];
  const firstSender = senders[0];

  msgEl.innerHTML = msgs.map(m => {
    const isSent = m.sender !== firstSender;
    const ts = m.timestamp ? new Date(m.timestamp).toLocaleString(undefined, {month:'short',day:'numeric',hour:'2-digit',minute:'2-digit'}) : '';
    return `<div class="sim-bubble ${isSent ? 'sim-bubble-sent' : 'sim-bubble-received'}">
        <span class="sim-msg-sender">${esc(m.sender)}</span>
        <span class="sim-msg-text">${esc(m.text)}</span>
        <span class="sim-msg-time">${ts}</span>
    </div>`;
  }).join('');
  msgEl.scrollTop = msgEl.scrollHeight;
}

async function loadDashboard() {
  const dashEl = document.getElementById('dashboard');
  dashEl.innerHTML = '<div class="empty-state"><span class="spinner"></span> Calculating stats...</div>';
  
  const stats = await fetchJSON(`/api/chats/${encodeURIComponent(currentChat)}/stats`);
  
  let awardsHtml = '';
  if (stats.awards && Object.keys(stats.awards).length > 0) {
      awardsHtml = '<div class="awards-grid">' + 
          Object.entries(stats.awards).map(([k,v]) => `<div class="award-card"><span class="award-title">${esc(k)}</span><span class="award-winner">${esc(v)}</span></div>`).join('')
      + '</div>';
  }

  let topSendersHtml = stats.top_senders.map(s => `<div style="display:flex;justify-content:space-between;margin-bottom:8px;font-size:0.85rem;"><span style="color:#fff">${esc(s.name)}</span><span style="color:var(--accent-teal)">${s.count} msgs</span></div>`).join('');

  dashEl.innerHTML = `
    <div class="stat-grid">
      <div class="bento-card"><div class="stat-value">${stats.total_messages.toLocaleString()}</div><div class="stat-label">Total Messages</div></div>
      <div class="bento-card"><div class="stat-value">${stats.total_words.toLocaleString()}</div><div class="stat-label">Total Words</div></div>
    </div>
    ${awardsHtml}
    <div class="chart-grid">
        <div class="chart-container"><canvas id="hourChart"></canvas></div>
        <div class="chart-container"><canvas id="dayChart"></canvas></div>
    </div>
    <div class="bento-card">
        <div class="stat-label" style="margin-bottom:12px;color:var(--text-primary);">Top Contributors</div>
        ${topSendersHtml}
    </div>
  `;

  if (hourChart) hourChart.destroy();
  if (dayChart) dayChart.destroy();

  const ctxH = document.getElementById('hourChart').getContext('2d');
  hourChart = new Chart(ctxH, {
      type: 'bar',
      data: {
          labels: Array.from({length:24}, (_,i) => i+":00"),
          datasets: [{ label: 'Messages', data: Object.values(stats.activity_by_hour), backgroundColor: '#00d4aa', borderRadius: 4 }]
      },
      options: { responsive: true, maintainAspectRatio: false, scales: { y: { beginAtZero: true } }, plugins:{legend:{display:false}} }
  });

  const ctxD = document.getElementById('dayChart').getContext('2d');
  dayChart = new Chart(ctxD, {
      type: 'bar',
      data: {
          labels: ['Mon','Tue','Wed','Thu','Fri','Sat','Sun'],
          datasets: [{ label: 'Messages', data: Object.values(stats.activity_by_day), backgroundColor: '#00b4d8', borderRadius: 4 }]
      },
      options: { responsive: true, maintainAspectRatio: false, scales: { y: { beginAtZero: true } }, plugins:{legend:{display:false}} }
  });
}

function setButtons(disabled) {
  document.querySelectorAll('#insightBtns button').forEach(b => b.disabled = disabled);
  document.getElementById('sendBtn').disabled = disabled;
}

async function doInsight(type) {
  if (!currentChat) return;
  setButtons(true);
  document.getElementById('ai-output-text').innerHTML = `<span class="spinner"></span> Analyzing ${type.replace('_', ' ')}...`;
  try {
    const data = await fetchJSON(`/api/chats/${encodeURIComponent(currentChat)}/insights`, {
        method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({type})
    });
    document.getElementById('ai-output-text').innerHTML = formatAI(data.insight || data.error);
  } catch(e) { document.getElementById('ai-output-text').innerHTML = 'Error: ' + esc(e.message); }
  setButtons(false);
}

async function doAnalyze() {
  if (!currentChat) return;
  setButtons(true);
  document.getElementById('ai-output-text').innerHTML = `<span class="spinner"></span> Running full analysis...`;
  try {
    const data = await fetchJSON('/api/analyze', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({chat_name:currentChat})});
    if (data.error) { document.getElementById('ai-output-text').innerHTML = esc(data.error); }
    else {
      const sections = ['summary','sentiment','topics','relationships','timeline'];
      const body = sections.map(s => data[s] ? `<div style="margin-top:16px;border-top:1px solid var(--border-glass);padding-top:8px"><div style="color:var(--accent-teal);font-weight:700;font-family:var(--font-title)">${s.charAt(0).toUpperCase()+s.slice(1)}</div>${formatAI(data[s])}</div>` : '').join('');
      document.getElementById('ai-output-text').innerHTML = body;
    }
  } catch(e) { document.getElementById('ai-output-text').innerHTML = 'Error: ' + esc(e.message); }
  setButtons(false);
}

async function doAsk() {
  const input = document.getElementById('askInput');
  const question = input.value.trim();
  if (!question) return;
  input.value = '';

  setButtons(true);
  document.getElementById('ai-output-text').innerHTML = `<span class="spinner"></span> Thinking...`;
  try {
    const data = await fetchJSON('/api/ask', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({question, chat_name:currentChat})});
    document.getElementById('ai-output-text').innerHTML = `<div style="margin-bottom:10px;color:var(--text-secondary);font-size:0.75rem">Q: ${esc(question)}</div>${formatAI(data.answer)}`;
  } catch(e) { document.getElementById('ai-output-text').innerHTML = 'Error: ' + esc(e.message); }
  setButtons(false);
}

// Modal Logic
function openImportModal() { document.getElementById('importModal').classList.add('open'); }
function closeImportModal() { document.getElementById('importModal').classList.remove('open'); }

function switchModalTab(tab) {
  document.querySelectorAll('.modal-tab').forEach(el => el.classList.remove('active'));
  document.querySelectorAll('.modal-pane').forEach(el => el.classList.remove('active'));
  event.target.classList.add('active');
  document.getElementById('pane-' + tab).classList.add('active');
}

const fileDrop = document.getElementById('fileDrop');
const fileInput = document.getElementById('fileInput');

fileDrop.addEventListener('dragover', (e) => { e.preventDefault(); fileDrop.classList.add('dragover'); });
fileDrop.addEventListener('dragleave', () => fileDrop.classList.remove('dragover'));
fileDrop.addEventListener('drop', (e) => {
  e.preventDefault(); fileDrop.classList.remove('dragover');
  if (e.dataTransfer.files.length) handleFileUpload(e.dataTransfer.files[0]);
});
fileInput.addEventListener('change', (e) => {
  if (e.target.files.length) handleFileUpload(e.target.files[0]);
});

async function handleFileUpload(file) {
  const isWa = file.name.endsWith('.txt');
  const isTg = file.name.endsWith('.json');
  if (!isWa && !isTg) return alert('Only .txt (WhatsApp) or .json (Telegram) allowed.');
  
  const status = document.getElementById('uploadStatus');
  status.textContent = 'Uploading and parsing...';
  
  const formData = new FormData();
  formData.append('file', file);
  
  try {
    const ep = isWa ? '/api/upload/whatsapp' : '/api/upload/telegram';
    const r = await fetch(ep, { method: 'POST', body: formData });
    const data = await r.json();
    if (data.error) throw new Error(data.error);
    status.textContent = `Success! Ingested ${data.count} messages.`;
    setTimeout(() => { status.textContent = ''; closeImportModal(); loadChats(); loadGlobalSummary(); }, 1500);
  } catch (e) {
    status.textContent = 'Error: ' + e.message;
  }
}

let currentPhoneHash = '';
async function sendTgCode() {
  const phone = document.getElementById('tgPhone').value.trim();
  if (!phone) return alert('Enter phone number');
  const btn = document.getElementById('btnSendCode');
  const status = document.getElementById('tgStatus');
  btn.disabled = true; status.textContent = 'Sending code...';
  
  try {
    const data = await fetchJSON('/api/telegram/auth/send_code', {
      method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({phone})
    });
    if (data.error) throw new Error(data.error);
    if (data.phone_code_hash === "ALREADY_AUTHORIZED") {
      status.textContent = "Already authorized! Fetching chats...";
      const v = await fetchJSON('/api/telegram/auth/verify', {
        method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({phone, code:'already', phone_code_hash:'already'})
      });
      if (v.error) throw new Error(v.error);
      status.textContent = `Synced ${v.count} messages.`;
      setTimeout(() => { closeImportModal(); loadChats(); loadGlobalSummary(); }, 1500);
    } else {
      currentPhoneHash = data.phone_code_hash;
      document.getElementById('step-phone').style.display = 'none';
      document.getElementById('step-code').style.display = 'block';
      status.textContent = 'Code sent via Telegram app.';
    }
  } catch(e) { status.textContent = 'Error: ' + e.message; }
  btn.disabled = false;
}

async function verifyTgCode() {
  const code = document.getElementById('tgCode').value.trim();
  const phone = document.getElementById('tgPhone').value.trim();
  if (!code) return alert('Enter code');
  const btn = document.getElementById('btnVerifyCode');
  const status = document.getElementById('tgStatus');
  btn.disabled = true; status.textContent = 'Verifying and syncing...';
  
  try {
    const data = await fetchJSON('/api/telegram/auth/verify', {
      method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({phone, code, phone_code_hash: currentPhoneHash})
    });
    if (data.error) throw new Error(data.error);
    status.textContent = `Success! Synced ${data.count} messages.`;
    setTimeout(() => { closeImportModal(); loadChats(); loadGlobalSummary(); }, 1500);
  } catch(e) { status.textContent = 'Error: ' + e.message; }
  btn.disabled = false;
}

async function loadGlobalSummary() {
  const container = document.getElementById('globalSummaryBody');
  try {
    const data = await fetchJSON('/api/global_summarize');
    container.innerHTML = formatAI(data.summary);
  } catch(e) {
    container.innerHTML = 'Error loading global summary: ' + esc(e.message);
  }
}

// Init
loadChats();
loadGlobalSummary();
