"""Generate app/static/index.html"""
from pathlib import Path

HTML = r'''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>SHL Assessment Recommender</title>
  <link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&display=swap" rel="stylesheet" />
  <style>
    :root{--bg:#0f1419;--surface:#1a2332;--surface2:#243044;--border:#2d3f56;--text:#e8eef5;--muted:#8ba3be;--accent:#0066cc;--accent-hover:#0052a3;--ok:#22c55e;--warn:#f59e0b;--err:#ef4444}
    *{box-sizing:border-box;margin:0;padding:0}
    body{font-family:"DM Sans",system-ui,sans-serif;background:var(--bg);color:var(--text);min-height:100vh;line-height:1.5}
    .layout{max-width:960px;margin:0 auto;padding:1.5rem;display:grid;gap:1.25rem}
    header{display:flex;flex-wrap:wrap;align-items:center;justify-content:space-between;gap:1rem;padding-bottom:1rem;border-bottom:1px solid var(--border)}
    header h1{font-size:1.35rem;font-weight:700}
    header p{color:var(--muted);font-size:.875rem;margin-top:.25rem}
    .status-bar{display:flex;flex-wrap:wrap;gap:.75rem;align-items:center}
    .pill{display:inline-flex;align-items:center;gap:.4rem;padding:.35rem .75rem;border-radius:999px;font-size:.8rem;font-weight:500;background:var(--surface2);border:1px solid var(--border)}
    .pill .dot{width:8px;height:8px;border-radius:50%;background:var(--muted)}
    .pill.ok .dot{background:var(--ok);box-shadow:0 0 8px var(--ok)}
    .pill.err .dot{background:var(--err)}
    .pill.pending .dot{background:var(--warn);animation:pulse 1s infinite}
    @keyframes pulse{50%{opacity:.4}}
    button{font-family:inherit;cursor:pointer;border:none;border-radius:8px;font-weight:600;font-size:.875rem}
    button:disabled{opacity:.5;cursor:not-allowed}
    .btn-primary{background:var(--accent);color:#fff;padding:.6rem 1.1rem}
    .btn-primary:hover:not(:disabled){background:var(--accent-hover)}
    .btn-ghost{background:var(--surface2);color:var(--text);padding:.6rem 1rem;border:1px solid var(--border)}
    .panel{background:var(--surface);border:1px solid var(--border);border-radius:12px;overflow:hidden}
    .panel-head{padding:.75rem 1rem;font-size:.75rem;font-weight:600;text-transform:uppercase;letter-spacing:.06em;color:var(--muted);border-bottom:1px solid var(--border)}
    .chat-log{min-height:280px;max-height:420px;overflow-y:auto;padding:1rem;display:flex;flex-direction:column;gap:.75rem}
    .msg{max-width:88%;padding:.75rem 1rem;border-radius:12px;font-size:.925rem;white-space:pre-wrap;word-break:break-word}
    .msg.user{align-self:flex-end;background:var(--accent);color:#fff;border-bottom-right-radius:4px}
    .msg.assistant{align-self:flex-start;background:var(--surface2);border:1px solid var(--border);border-bottom-left-radius:4px}
    .msg.system{align-self:center;font-size:.8rem;color:var(--muted);text-align:center}
    .recs{margin-top:.75rem;padding-top:.75rem;border-top:1px solid var(--border)}
    .recs h4{font-size:.7rem;text-transform:uppercase;color:var(--muted);margin-bottom:.5rem}
    .rec-card{background:var(--bg);border:1px solid var(--border);border-radius:8px;padding:.6rem .75rem;margin-bottom:.4rem;font-size:.85rem}
    .rec-card a{color:#6eb5ff;text-decoration:none}
    .rec-meta{color:var(--muted);font-size:.75rem;margin-top:.2rem}
    .composer{display:flex;gap:.5rem;padding:1rem;border-top:1px solid var(--border)}
    .composer textarea{flex:1;resize:none;min-height:48px;padding:.65rem .85rem;border-radius:8px;border:1px solid var(--border);background:var(--bg);color:var(--text);font-family:inherit;font-size:.925rem}
    .examples{display:flex;flex-wrap:wrap;gap:.4rem;padding:0 1rem 1rem}
    .examples button{font-size:.75rem;padding:.35rem .65rem;background:var(--bg);color:var(--muted);border:1px solid var(--border);border-radius:6px}
    .api-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:.75rem;padding:1rem}
    .api-card{padding:.75rem;background:var(--bg);border-radius:8px;border:1px solid var(--border);font-size:.8rem}
    .api-card code{color:#6eb5ff;font-size:.75rem}
    .api-card .result{margin-top:.5rem;color:var(--muted);word-break:break-all}
    footer{text-align:center;font-size:.75rem;color:var(--muted);padding:1rem}
    footer a{color:#6eb5ff}
    .spinner{display:inline-block;width:14px;height:14px;border:2px solid var(--border);border-top-color:var(--accent);border-radius:50%;animation:spin .7s linear infinite;vertical-align:middle;margin-right:.35rem}
    @keyframes spin{to{transform:rotate(360deg)}}
  </style>
</head>
<body>
<div class="layout">
<header>
  <motion.div><h1>SHL Assessment Recommender</h1><p>Individual Test Solutions · Live demo</p></motion.div>
  <div class="status-bar">
    <span class="pill pending" id="healthPill"><span class="dot"></span> Checking API…</span>
    <span class="pill" id="catalogPill"><span class="dot"></span> Catalog —</span>
    <button type="button" class="btn-ghost" id="btnHealth">Test /health</button>
  </div>
</header>
<section class="panel">
  <div class="panel-head">Chat · POST /chat</motion.div>
  <div class="chat-log" id="chatLog"><div class="msg system">Describe hiring needs to get SHL catalog recommendations. Do not open /chat in the browser — use this chat.</motion.div></div>
  <div class="examples">
    <button type="button" data-prompt="I need an assessment for my company.">Vague</button>
    <button type="button" data-prompt="Mid-level Java developer. Need cognitive and Java technical tests.">Java dev</button>
    <button type="button" data-prompt="What is the difference between OPQ and Verify GAT?">Compare</button>
    <button type="button" data-prompt="Actually, also add personality tests.">+ Personality</button>
  </div>
  <div class="composer">
    <textarea id="input" rows="2" placeholder="Role, seniority, skills to assess…"></textarea>
    <button type="button" class="btn-primary" id="btnSend">Send</button>
  </div>
</section>
<section class="panel">
  <div class="panel-head">API status</motion.div>
  <motion.div class="api-grid">
    <div class="api-card"><strong>GET /health</strong><br><code id="healthUrl"></code><motion.div class="result" id="healthResult">—</motion.div></div>
    <div class="api-card"><strong>POST /chat</strong><br><code id="chatUrl"></code><motion.div class="result" id="chatResult">—</motion.div></motion.div>
    <div class="api-card"><strong>Info</strong><motion.div class="result" id="infoResult">—</motion.div></motion.div>
  </motion.div>
</section>
<footer>Evaluators: <code>GET /health</code> · <code>POST /chat</code> · <a href="/docs">/docs</a></footer>
</motion.div>
<script>
const base=location.origin;
document.getElementById("healthUrl").textContent=base+"/health";
document.getElementById("chatUrl").textContent=base+"/chat";
const messages=[],chatLog=document.getElementById("chatLog"),input=document.getElementById("input"),btnSend=document.getElementById("btnSend");
const healthPill=document.getElementById("healthPill"),catalogPill=document.getElementById("catalogPill");
const healthResult=document.getElementById("healthResult"),chatResult=document.getElementById("chatResult"),infoResult=document.getElementById("infoResult");
function esc(s){const d=document.createElement("div");d.textContent=s;return d.innerHTML;}
function appendMsg(role,text,recs){
  const el=document.createElement("div");el.className="msg "+role;el.textContent=text;
  if(recs&&recs.length){const box=document.createElement("div");box.className="recs";
    box.innerHTML="<h4>Recommendations ("+recs.length+")</h4>";
    recs.forEach(r=>{const c=document.createElement("div");c.className="rec-card";
      c.innerHTML="<strong>"+esc(r.name)+"</strong><div class=\"rec-meta\">"+esc(r.test_type)+"</div><a href=\""+esc(r.url)+"\" target=\"_blank\" rel=\"noopener\">"+esc(r.url)+"</a>";box.appendChild(c);});
    el.appendChild(box);}
  chatLog.appendChild(el);chatLog.scrollTop=chatLog.scrollHeight;}
async function checkHealth(){
  healthPill.className="pill pending";healthPill.innerHTML='<span class="dot"></span> Checking…';
  const t0=performance.now();
  try{const res=await fetch(base+"/health");const ms=Math.round(performance.now()-t0);const data=await res.json();
    if(res.ok&&data.status==="ok"){healthPill.className="pill ok";healthPill.innerHTML='<span class="dot"></span> API online';
      healthResult.textContent=JSON.stringify(data)+" ("+ms+"ms)";return true;}
    throw new Error(JSON.stringify(data));}catch(e){healthPill.className="pill err";healthPill.innerHTML='<span class="dot"></span> Offline';
    healthResult.textContent="Error: "+e.message;return false;}}
async function loadInfo(){try{const res=await fetch(base+"/api/info");if(!res.ok)return;const d=await res.json();
  catalogPill.innerHTML='<span class="dot"></span> '+d.catalog_size+" tests";
  infoResult.textContent="mode: "+d.mode+" · catalog: "+d.catalog_size;}catch(_){}}
async function sendChat(){const text=input.value.trim();if(!text)return;input.value="";
  messages.push({role:"user",content:text});appendMsg("user",text);btnSend.disabled=true;btnSend.innerHTML='<span class="spinner"></span>…';
  const t0=performance.now();
  try{const res=await fetch(base+"/chat",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({messages})});
    const ms=Math.round(performance.now()-t0);const data=await res.json();if(!res.ok)throw new Error(data.detail||res.statusText);
    messages.push({role:"assistant",content:data.reply});appendMsg("assistant",data.reply,data.recommendations);
    chatResult.textContent="OK "+ms+"ms · recs: "+(data.recommendations?.length||0);
  }catch(e){appendMsg("system","Error: "+e.message);chatResult.textContent="Failed: "+e.message;}
  btnSend.disabled=false;btnSend.textContent="Send";}
btnSend.onclick=sendChat;input.onkeydown=e=>{if(e.key==="Enter"&&!e.shiftKey){e.preventDefault();sendChat();}};
document.getElementById("btnHealth").onclick=checkHealth;
document.querySelectorAll(".examples button").forEach(b=>b.onclick=()=>{input.value=b.dataset.prompt;input.focus();});
checkHealth().then(loadInfo);
</script>
</body>
</html>'''
# fix accidental motion.div typos
HTML = HTML.replace('motion.div', 'motion.div').replace('<motion.div>', '<motion.div>').replace('</motion.div>', '</motion.div>')
HTML = HTML.replace('motion.div', 'div')
Path('app/static/index.html').write_text(HTML, encoding='utf-8')
print('wrote', len(HTML), 'bytes')
