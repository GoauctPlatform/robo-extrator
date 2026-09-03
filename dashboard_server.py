#!/usr/bin/env python3
"""
Parcel Auction Pipeline Dashboard
Run:  python3 dashboard_server.py
Open: http://localhost:5050

Requirements: pip install flask
"""
import os
import re
import threading
import subprocess
from flask import Flask, jsonify, request

CWD  = os.path.dirname(os.path.abspath(__file__))
app  = Flask(__name__)

SCRIPTS = {
    "data_parcel": ["python3", "-u", "data_parcel_auct.py"],
    "calendar":    ["python3", "-u", "download_auction_calendar.py"],
    "combine":     ["python3", "-u", "combine_auction_csvs.py"],
    "merge":       ["python3", "-u", "merge_auction_data.py"],
    "postgres":    ["python3", "-u", "generate_postgres_csvs.py"],
    "audit":       ["bash",           "organize_and_audit.sh"],
}

jobs  = {k: {"status": "idle", "lines": [], "process": None} for k in SCRIPTS}
_lock = threading.Lock()
ANSI  = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')


def run_job(key: str):
    cmd = SCRIPTS[key]
    with _lock:
        jobs[key].update(status="running", lines=[])
    try:
        env  = {**os.environ, "PYTHONUNBUFFERED": "1"}
        proc = subprocess.Popen(
            cmd, cwd=CWD,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, bufsize=1, env=env,
        )
        with _lock:
            jobs[key]["process"] = proc
        for line in iter(proc.stdout.readline, ""):
            with _lock:
                jobs[key]["lines"].append(ANSI.sub("", line))
        proc.wait()
        with _lock:
            jobs[key]["status"] = "done" if proc.returncode == 0 else "error"
            jobs[key]["process"] = None
    except Exception as exc:
        with _lock:
            jobs[key]["lines"].append(f"ERRO INTERNO: {exc}\n")
            jobs[key]["status"] = "error"
            jobs[key]["process"] = None


# ─────────────────────────── Routes ───────────────────────────

@app.route("/")
def index():
    return HTML

@app.route("/api/run/<key>", methods=["POST"])
def api_run(key):
    if key not in SCRIPTS:
        return jsonify(error="script desconhecido"), 400
    with _lock:
        if jobs[key]["status"] == "running":
            return jsonify(error="já em execução"), 409
    threading.Thread(target=run_job, args=(key,), daemon=True).start()
    return jsonify(ok=True)

@app.route("/api/kill/<key>", methods=["POST"])
def api_kill(key):
    with _lock:
        p = jobs[key].get("process")
    if p:
        try: p.terminate()
        except Exception: pass
    with _lock:
        jobs[key]["status"] = "idle"
    return jsonify(ok=True)

@app.route("/api/reset/<key>", methods=["POST"])
def api_reset(key):
    with _lock:
        if jobs[key]["status"] != "running":
            jobs[key].update(status="idle", lines=[], process=None)
    return jsonify(ok=True)

@app.route("/api/status")
def api_status():
    with _lock:
        return jsonify({k: jobs[k]["status"] for k in jobs})

@app.route("/api/logs/<key>")
def api_logs(key):
    frm = int(request.args.get("from", 0))
    if key not in jobs:
        return jsonify(lines=[], status="idle")
    with _lock:
        return jsonify(lines=jobs[key]["lines"][frm:], status=jobs[key]["status"])


# ─────────────────────────── HTML ───────────────────────────

HTML = """<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Parcel Auction · Pipeline</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
<style>
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}

:root{
  --bg:#080c18;
  --surface:#0f1525;
  --glass:rgba(255,255,255,.04);
  --border:rgba(255,255,255,.08);
  --p1:#8b5cf6;
  --p2:#06b6d4;
  --p3:#10b981;
  --ok:#22c55e;
  --err:#ef4444;
  --run:#f59e0b;
  --text:#e2e8f0;
  --muted:#64748b;
  --font:'Inter',sans-serif;
  --mono:'JetBrains Mono',monospace;
}

body{
  font-family:var(--font);
  background:var(--bg);
  color:var(--text);
  min-height:100vh;
}

body::before{
  content:'';
  position:fixed;inset:0;
  background:
    radial-gradient(ellipse 70% 50% at 15% 5%,rgba(139,92,246,.13) 0%,transparent 60%),
    radial-gradient(ellipse 50% 40% at 85% 90%,rgba(6,182,212,.09) 0%,transparent 60%),
    radial-gradient(ellipse 40% 30% at 50% 50%,rgba(16,185,129,.05) 0%,transparent 70%);
  pointer-events:none;z-index:0;
}

/* ── Header ── */
header{
  position:sticky;top:0;z-index:100;
  background:rgba(8,12,24,.88);
  backdrop-filter:blur(20px);
  border-bottom:1px solid var(--border);
  padding:0 28px;
}
.header-inner{
  max-width:1360px;margin:0 auto;
  height:62px;display:flex;align-items:center;justify-content:space-between;gap:16px;
}
.logo{display:flex;align-items:center;gap:12px}
.logo-icon{
  width:38px;height:38px;
  background:linear-gradient(135deg,#8b5cf6,#06b6d4);
  border-radius:11px;display:flex;align-items:center;justify-content:center;font-size:20px;
  box-shadow:0 0 20px rgba(139,92,246,.3);
}
.logo-text h1{font-size:15px;font-weight:700;letter-spacing:-.02em}
.logo-text p{font-size:11px;color:var(--muted);margin-top:1px}

/* ── Layout ── */
main{
  position:relative;z-index:1;
  max-width:1360px;margin:0 auto;
  padding:24px 28px 80px;
}

/* ── Buttons ── */
.btn{
  display:inline-flex;align-items:center;gap:6px;
  padding:7px 15px;border-radius:8px;
  font-size:12.5px;font-weight:600;font-family:var(--font);
  cursor:pointer;border:1px solid transparent;
  transition:all .18s ease;white-space:nowrap;
}
.btn:disabled{opacity:.35;cursor:not-allowed;transform:none!important}
.btn-green{background:rgba(34,197,94,.12);border-color:rgba(34,197,94,.3);color:#86efac}
.btn-green:hover:not(:disabled){background:rgba(34,197,94,.22);transform:translateY(-1px);box-shadow:0 4px 14px rgba(34,197,94,.2)}
.btn-red{background:rgba(239,68,68,.1);border-color:rgba(239,68,68,.25);color:#fca5a5}
.btn-red:hover:not(:disabled){background:rgba(239,68,68,.22);transform:translateY(-1px)}
.btn-ghost{background:transparent;border-color:var(--border);color:var(--muted)}
.btn-ghost:hover:not(:disabled){background:var(--glass);color:var(--text);border-color:rgba(255,255,255,.15)}
.btn-amber{background:rgba(245,158,11,.12);border-color:rgba(245,158,11,.3);color:#fcd34d}
.btn-amber:hover:not(:disabled){background:rgba(245,158,11,.24);transform:translateY(-1px);box-shadow:0 4px 14px rgba(245,158,11,.2)}

/* ── Badges ── */
.badge{
  display:inline-flex;align-items:center;gap:5px;
  padding:4px 10px;border-radius:999px;
  font-size:11px;font-weight:600;letter-spacing:.04em;text-transform:uppercase;
}
.badge-idle  {background:rgba(100,116,139,.12);color:#94a3b8;border:1px solid rgba(100,116,139,.22)}
.badge-running{background:rgba(245,158,11,.12);color:#fcd34d;border:1px solid rgba(245,158,11,.28);animation:pulse-a 1.8s ease infinite}
.badge-done  {background:rgba(34,197,94,.1);color:#86efac;border:1px solid rgba(34,197,94,.28)}
.badge-error {background:rgba(239,68,68,.1);color:#fca5a5;border:1px solid rgba(239,68,68,.28)}
@keyframes pulse-a{0%,100%{box-shadow:0 0 0 0 rgba(245,158,11,0)}50%{box-shadow:0 0 0 4px rgba(245,158,11,.15)}}
.badge-dot{width:6px;height:6px;border-radius:50%;background:currentColor;flex-shrink:0}
.badge-running .badge-dot{animation:blink 1s step-start infinite}
@keyframes blink{50%{opacity:0}}

/* ── Phase Section ── */
.phase-section{
  margin-top:24px;border-radius:16px;
  border:1px solid var(--border);
  background:var(--glass);
  overflow:hidden;
  transition:opacity .35s,filter .35s;
}
.phase-section.locked{opacity:.45;filter:grayscale(.4);pointer-events:none}

.phase-header{
  padding:16px 22px;display:flex;align-items:center;gap:14px;
  border-bottom:1px solid var(--border);position:relative;
}
.phase-header::before{
  content:'';position:absolute;left:0;top:0;bottom:0;
  width:3px;border-radius:0 2px 2px 0;
  background:var(--phase-color,#8b5cf6);
}
.phase-num{
  width:28px;height:28px;border-radius:8px;
  background:rgba(var(--phase-rgb,139,92,246),.18);
  border:1px solid rgba(var(--phase-rgb,139,92,246),.35);
  color:var(--phase-color,#8b5cf6);
  display:flex;align-items:center;justify-content:center;
  font-size:13px;font-weight:700;flex-shrink:0;
}
.phase-title h2{font-size:14px;font-weight:700;letter-spacing:-.02em}
.phase-title p{font-size:11.5px;color:var(--muted);margin-top:2px}
.phase-lock{
  margin-left:auto;display:flex;align-items:center;gap:6px;
  padding:5px 12px;background:rgba(100,116,139,.1);
  border:1px solid rgba(100,116,139,.2);
  border-radius:8px;font-size:11.5px;color:#64748b;font-weight:500;
}
.phase-section:not(.locked) .phase-lock{display:none}

.scripts-grid{
  padding:18px;
  display:grid;
  grid-template-columns:repeat(auto-fit,minmax(400px,1fr));
  gap:14px;
}

/* ── Script Card ── */
.script-card{
  background:rgba(255,255,255,.022);
  border:1px solid var(--border);border-radius:12px;overflow:hidden;
  transition:border-color .25s,box-shadow .25s;
}
.script-card.running{border-color:rgba(245,158,11,.35);box-shadow:0 0 0 1px rgba(245,158,11,.08),inset 0 0 60px rgba(245,158,11,.025)}
.script-card.done   {border-color:rgba(34,197,94,.28)}
.script-card.error  {border-color:rgba(239,68,68,.28)}

.progress-bar{height:2px;background:rgba(255,255,255,.05);overflow:hidden}
.progress-fill{height:100%;width:0;background:linear-gradient(90deg,#8b5cf6,#06b6d4);transition:width .3s}
.running .progress-fill{width:100%;animation:indeterminate 1.6s ease-in-out infinite;transform-origin:left}
@keyframes indeterminate{0%{transform:translateX(-100%)}100%{transform:translateX(300%)}}

.card-top{
  padding:12px 16px;display:flex;align-items:center;justify-content:space-between;gap:10px;
  border-bottom:1px solid var(--border);
}
.card-identity{display:flex;align-items:center;gap:10px}
.card-icon{font-size:22px;width:34px;text-align:center;flex-shrink:0}
.card-name{font-size:13.5px;font-weight:600}
.card-filename{font-size:11px;color:var(--muted);font-family:var(--mono);margin-top:2px}
.card-actions-row{
  padding:9px 16px;display:flex;gap:8px;
  border-bottom:1px solid var(--border);flex-wrap:wrap;
}

/* ── Terminal ── */
.terminal{
  background:#060810;font-family:var(--mono);
  font-size:11.5px;line-height:1.65;
  padding:10px 12px;height:210px;overflow-y:auto;
  scroll-behavior:smooth;
}
.terminal::-webkit-scrollbar{width:4px}
.terminal::-webkit-scrollbar-thumb{background:rgba(255,255,255,.09);border-radius:4px}
.log-line{padding:1px 0;white-space:pre-wrap;word-break:break-word}
.log-ok  {color:#4ade80}
.log-warn{color:#fbbf24}
.log-err {color:#f87171}
.log-info{color:#67e8f9}
.log-skip{color:#475569}
.log-def {color:#94a3b8}
.log-empty{color:#334155;font-size:11px;padding:4px 0}

/* ── Audit section ── */
.audit-wrap{
  margin-top:24px;padding:18px 22px;
  border-radius:16px;border:1px solid rgba(245,158,11,.2);
  background:rgba(245,158,11,.03);
}
.audit-header{display:flex;align-items:center;gap:14px;flex-wrap:wrap}
.audit-info h3{font-size:14px;font-weight:700;color:#fcd34d}
.audit-info p{font-size:11.5px;color:#92400e;margin-top:2px}
.audit-actions{margin-left:auto;display:flex;align-items:center;gap:10px}
.audit-term-wrap{margin-top:14px;display:none}

/* ── Phase color vars ── */
#phase1{--phase-color:#8b5cf6;--phase-rgb:139,92,246}
#phase2{--phase-color:#06b6d4;--phase-rgb:6,182,212}
#phase3{--phase-color:#10b981;--phase-rgb:16,185,129}

/* ── Responsive ── */
@media(max-width:600px){
  .scripts-grid{grid-template-columns:1fr}
  main{padding:16px 16px 60px}
}
</style>
</head>
<body>

<header>
  <div class="header-inner">
    <div class="logo">
      <div class="logo-icon">🏠</div>
      <div class="logo-text">
        <h1>Parcel Auction Pipeline</h1>
        <p>Dashboard de execução do pipeline de dados</p>
      </div>
    </div>
    <span class="badge badge-idle" id="global-badge">
      <span class="badge-dot"></span>Sistema ocioso
    </span>
  </div>
</header>

<main>

<!-- ═══════════ FASE 1 ═══════════ -->
<section class="phase-section" id="phase1">
  <div class="phase-header">
    <div class="phase-num">1</div>
    <div class="phase-title">
      <h2>Coleta de Dados</h2>
      <p>Scraping dos parcels + download do calendário de leilões</p>
    </div>
    <div class="phase-lock">🔒 Aguardando liberação</div>
  </div>
  <div class="scripts-grid">

    <!-- data_parcel_auct -->
    <div class="script-card" id="card-data_parcel">
      <div class="progress-bar"><div class="progress-fill"></div></div>
      <div class="card-top">
        <div class="card-identity">
          <span class="card-icon">🕷️</span>
          <div>
            <div class="card-name">Scraping de Parcels</div>
            <div class="card-filename">data_parcel_auct.py</div>
          </div>
        </div>
        <span class="badge badge-idle" id="badge-data_parcel"><span class="badge-dot"></span>Aguardando</span>
      </div>
      <div class="card-actions-row">
        <button class="btn btn-green" id="btn-start-data_parcel" onclick="startScript('data_parcel')">▶ Iniciar</button>
        <button class="btn btn-red"   id="btn-stop-data_parcel"  onclick="killScript('data_parcel')"  disabled>⏹ Parar</button>
        <button class="btn btn-ghost" id="btn-reset-data_parcel" onclick="resetScript('data_parcel')" disabled>↺ Resetar</button>
      </div>
      <div class="terminal" id="terminal-data_parcel"><div class="log-empty">Aguardando início...</div></div>
    </div>

    <!-- download_auction_calendar -->
    <div class="script-card" id="card-calendar">
      <div class="progress-bar"><div class="progress-fill"></div></div>
      <div class="card-top">
        <div class="card-identity">
          <span class="card-icon">📅</span>
          <div>
            <div class="card-name">Download Calendário</div>
            <div class="card-filename">download_auction_calendar.py</div>
          </div>
        </div>
        <span class="badge badge-idle" id="badge-calendar"><span class="badge-dot"></span>Aguardando</span>
      </div>
      <div class="card-actions-row">
        <button class="btn btn-green" id="btn-start-calendar" onclick="startScript('calendar')">▶ Iniciar</button>
        <button class="btn btn-red"   id="btn-stop-calendar"  onclick="killScript('calendar')"  disabled>⏹ Parar</button>
        <button class="btn btn-ghost" id="btn-reset-calendar" onclick="resetScript('calendar')" disabled>↺ Resetar</button>
      </div>
      <div class="terminal" id="terminal-calendar"><div class="log-empty">Aguardando início...</div></div>
    </div>

  </div>
</section>

<!-- ═══════════ FASE 2 ═══════════ -->
<section class="phase-section locked" id="phase2">
  <div class="phase-header">
    <div class="phase-num">2</div>
    <div class="phase-title">
      <h2>Combinação &amp; Merge</h2>
      <p>Unifica os CSVs e realiza o merge dos dados de leilão</p>
    </div>
    <div class="phase-lock">🔒 Complete a Fase 1 primeiro</div>
  </div>
  <div class="scripts-grid">

    <!-- combine_auction_csvs -->
    <div class="script-card" id="card-combine">
      <div class="progress-bar"><div class="progress-fill"></div></div>
      <div class="card-top">
        <div class="card-identity">
          <span class="card-icon">🔗</span>
          <div>
            <div class="card-name">Combinar CSVs</div>
            <div class="card-filename">combine_auction_csvs.py</div>
          </div>
        </div>
        <span class="badge badge-idle" id="badge-combine"><span class="badge-dot"></span>Aguardando</span>
      </div>
      <div class="card-actions-row">
        <button class="btn btn-green" id="btn-start-combine" onclick="startScript('combine')">▶ Iniciar</button>
        <button class="btn btn-red"   id="btn-stop-combine"  onclick="killScript('combine')"  disabled>⏹ Parar</button>
        <button class="btn btn-ghost" id="btn-reset-combine" onclick="resetScript('combine')" disabled>↺ Resetar</button>
      </div>
      <div class="terminal" id="terminal-combine"><div class="log-empty">Aguardando início...</div></div>
    </div>

    <!-- merge_auction_data -->
    <div class="script-card" id="card-merge">
      <div class="progress-bar"><div class="progress-fill"></div></div>
      <div class="card-top">
        <div class="card-identity">
          <span class="card-icon">⚙️</span>
          <div>
            <div class="card-name">Merge de Dados</div>
            <div class="card-filename">merge_auction_data.py</div>
          </div>
        </div>
        <span class="badge badge-idle" id="badge-merge"><span class="badge-dot"></span>Aguardando</span>
      </div>
      <div class="card-actions-row">
        <button class="btn btn-green" id="btn-start-merge" onclick="startScript('merge')">▶ Iniciar</button>
        <button class="btn btn-red"   id="btn-stop-merge"  onclick="killScript('merge')"  disabled>⏹ Parar</button>
        <button class="btn btn-ghost" id="btn-reset-merge" onclick="resetScript('merge')" disabled>↺ Resetar</button>
      </div>
      <div class="terminal" id="terminal-merge"><div class="log-empty">Aguardando início...</div></div>
    </div>

  </div>
</section>

<!-- ═══════════ FASE 3 ═══════════ -->
<section class="phase-section locked" id="phase3">
  <div class="phase-header">
    <div class="phase-num">3</div>
    <div class="phase-title">
      <h2>Geração dos CSVs PostgreSQL</h2>
      <p>Gera os arquivos finais prontos para importação no banco</p>
    </div>
    <div class="phase-lock">🔒 Complete a Fase 2 primeiro</div>
  </div>
  <div class="scripts-grid">

    <!-- generate_postgres_csvs -->
    <div class="script-card" id="card-postgres">
      <div class="progress-bar"><div class="progress-fill"></div></div>
      <div class="card-top">
        <div class="card-identity">
          <span class="card-icon">🗄️</span>
          <div>
            <div class="card-name">Gerar CSVs PostgreSQL</div>
            <div class="card-filename">generate_postgres_csvs.py</div>
          </div>
        </div>
        <span class="badge badge-idle" id="badge-postgres"><span class="badge-dot"></span>Aguardando</span>
      </div>
      <div class="card-actions-row">
        <button class="btn btn-green" id="btn-start-postgres" onclick="startScript('postgres')">▶ Iniciar</button>
        <button class="btn btn-red"   id="btn-stop-postgres"  onclick="killScript('postgres')"  disabled>⏹ Parar</button>
        <button class="btn btn-ghost" id="btn-reset-postgres" onclick="resetScript('postgres')" disabled>↺ Resetar</button>
      </div>
      <div class="terminal" id="terminal-postgres"><div class="log-empty">Aguardando início...</div></div>
    </div>

  </div>
</section>

<!-- ═══════════ AUDIT ═══════════ -->
<div class="audit-wrap">
  <div class="audit-header">
    <span style="font-size:26px">🧹</span>
    <div class="audit-info">
      <h3>Limpar &amp; Auditar</h3>
      <p>Move arquivos para pasta de auditoria e reseta todos os checkpoints</p>
    </div>
    <div class="audit-actions">
      <span class="badge badge-idle" id="badge-audit"><span class="badge-dot"></span>Pronto</span>
      <button class="btn btn-amber" id="btn-start-audit" onclick="startScript('audit')">🧹 Executar Limpeza</button>
      <button class="btn btn-red"   id="btn-stop-audit"  onclick="killScript('audit')" disabled>⏹ Parar</button>
    </div>
  </div>
  <div class="audit-term-wrap" id="audit-term-wrap">
    <div class="terminal" id="terminal-audit" style="height:130px;border-radius:10px;margin-top:0"></div>
  </div>
</div>

</main>

<script>
// ─────────────────── State ───────────────────
const cursors = {data_parcel:0, calendar:0, combine:0, merge:0, postgres:0, audit:0};
const KEYS    = Object.keys(cursors);

const STATUS_LABEL = {idle:'Aguardando', running:'Rodando', done:'Concluído', error:'Erro'};
const STATUS_BADGE = {idle:'badge-idle', running:'badge-running', done:'badge-done', error:'badge-error'};

// ─────────────────── Log colorizer ───────────────────
function colorize(line) {
  const t   = line.trimEnd();
  if (!t) return '<div class="log-line log-def">&nbsp;</div>';
  const esc = t.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
  if (/✅|conclu|salvo|saved|done|success|finalizado/i.test(esc))
    return `<div class="log-line log-ok">${esc}</div>`;
  if (/traceback|exception|critical/i.test(esc))
    return `<div class="log-line log-err">${esc}</div>`;
  if (/⚠️|erro|error|warning|timeout|falha|fail/i.test(esc))
    return `<div class="log-line log-warn">${esc}</div>`;
  if (/🔐|🚀|📥|📦|📂|🎉|🏠|🌐/i.test(esc))
    return `<div class="log-line log-info">${esc}</div>`;
  if (/⏩|pulando|skip/i.test(esc))
    return `<div class="log-line log-skip">${esc}</div>`;
  return `<div class="log-line log-def">${esc}</div>`;
}

// ─────────────────── API ───────────────────
async function startScript(key) {
  cursors[key] = 0;
  const term = document.getElementById(`terminal-${key}`);
  if (term) term.innerHTML = '';
  try { await fetch(`/api/run/${key}`, {method:'POST'}); } catch(e) {}
}
async function killScript(key) {
  try { await fetch(`/api/kill/${key}`, {method:'POST'}); } catch(e) {}
}
async function resetScript(key) {
  cursors[key] = 0;
  const term = document.getElementById(`terminal-${key}`);
  if (term) term.innerHTML = '<div class="log-empty">Aguardando início...</div>';
  try { await fetch(`/api/reset/${key}`, {method:'POST'}); } catch(e) {}
}

// ─────────────────── Update card UI ───────────────────
function updateCard(key, status) {
  const card  = document.getElementById(`card-${key}`);
  if (card) card.className = `script-card ${status}`;

  const badge = document.getElementById(`badge-${key}`);
  if (badge) {
    badge.className = `badge ${STATUS_BADGE[status]}`;
    badge.innerHTML = `<span class="badge-dot"></span>${STATUS_LABEL[status]}`;
  }

  const bStart = document.getElementById(`btn-start-${key}`);
  const bStop  = document.getElementById(`btn-stop-${key}`);
  const bReset = document.getElementById(`btn-reset-${key}`);
  if (bStart) bStart.disabled = (status === 'running');
  if (bStop)  bStop.disabled  = (status !== 'running');
  if (bReset) bReset.disabled = (status === 'running' || status === 'idle');

  // Show audit terminal when audit starts/done
  if (key === 'audit' && status !== 'idle') {
    document.getElementById('audit-term-wrap').style.display = 'block';
  }
}

// ─────────────────── Append logs ───────────────────
async function fetchLogs(key) {
  try {
    const res  = await fetch(`/api/logs/${key}?from=${cursors[key]}`);
    const data = await res.json();
    if (!data.lines.length) return;
    const term = document.getElementById(`terminal-${key}`);
    if (!term) return;
    const ph = term.querySelector('.log-empty');
    if (ph) ph.remove();
    data.lines.forEach(l => term.insertAdjacentHTML('beforeend', colorize(l)));
    cursors[key] += data.lines.length;
    term.scrollTop = term.scrollHeight;
  } catch(e) {}
}

// ─────────────────── Phase unlock ───────────────────
function updatePhases(s) {
  const p1done = s.data_parcel === 'done' && s.calendar === 'done';
  const p2done = s.combine === 'done' && s.merge === 'done';
  const p2 = document.getElementById('phase2');
  const p3 = document.getElementById('phase3');
  if (p2) p2.classList.toggle('locked', !p1done);
  if (p3) p3.classList.toggle('locked', !p2done);

  // Merge button only unlocked after combine done
  const bStartMerge = document.getElementById('btn-start-merge');
  if (bStartMerge) {
    const combineOk = s.combine === 'done';
    if (!combineOk && s.merge !== 'running') bStartMerge.disabled = true;
    else if (combineOk && s.merge !== 'running') bStartMerge.disabled = false;
  }

  // Global badge
  const gb = document.getElementById('global-badge');
  if (!gb) return;
  const anyRunning = KEYS.some(k => s[k] === 'running');
  const anyError   = KEYS.some(k => s[k] === 'error');
  if (anyRunning) {
    gb.className = 'badge badge-running';
    gb.innerHTML = '<span class="badge-dot"></span>Processando...';
  } else if (anyError) {
    gb.className = 'badge badge-error';
    gb.innerHTML = '<span class="badge-dot"></span>Erro detectado';
  } else if (p1done && p2done && s.postgres === 'done') {
    gb.className = 'badge badge-done';
    gb.innerHTML = '<span class="badge-dot"></span>Pipeline completo ✅';
  } else {
    gb.className = 'badge badge-idle';
    gb.innerHTML = '<span class="badge-dot"></span>Sistema ocioso';
  }
}

// ─────────────────── Main poll loop ───────────────────
async function poll() {
  try {
    const res = await fetch('/api/status');
    const s   = await res.json();
    KEYS.forEach(k => updateCard(k, s[k] || 'idle'));
    for (const k of KEYS) {
      if (s[k] === 'running' || cursors[k] > 0) await fetchLogs(k);
    }
    updatePhases(s);
  } catch(e) {}
}

poll();
setInterval(poll, 1500);
</script>
</body>
</html>"""


if __name__ == "__main__":
    print("\n" + "═" * 52)
    print("  🏠  Parcel Auction Pipeline Dashboard")
    print("  🌐  Acesse: http://localhost:5050")
    print("═" * 52 + "\n")
    app.run("0.0.0.0", 5050, debug=False, threaded=True)
